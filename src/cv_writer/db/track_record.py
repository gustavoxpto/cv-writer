"""Track record persistence (spec criteria 29-31).

`Application` is the one record of a generated application: date, company, country, area,
role, ingestion source/tier, match score, output language, page count, skills featured, output
artifact paths, and the profile-bullet ids the CV was built from (criterion 29). No generation
pipeline calls this yet (slice 4) — insert_application()/list_applications() are exercised
directly against constructed records for now, per the spec's own slice ordering.

Skills and bullet-source ids are stored in their own join tables (application_skills,
application_bullet_sources) rather than as a serialized blob column, so criterion 30's "sorted
and filtered by ... skill" can be a real SQL join instead of an application-side scan.
"""

from __future__ import annotations

import sqlite3
from datetime import date

from pydantic import BaseModel, Field

# Whitelisted so sort_by can never be used to inject arbitrary SQL (criterion 30).
_SORTABLE_COLUMNS = {
    "date": "application_date",
    "application_date": "application_date",
    "company": "company",
    "country": "country",
    "area": "area",
}


class Application(BaseModel):
    """One generated application, ready to persist (criterion 29)."""

    id: int | None = None
    application_date: date
    company: str = Field(min_length=1)
    country: str = Field(min_length=1)
    area: str = Field(min_length=1)
    role_title: str = Field(min_length=1)
    source: str = Field(min_length=1)  # a URL, or the literal "pasted"
    ingestion_tier: int | None = None
    match_score: float | None = None
    output_language: str = Field(min_length=1)
    page_count: int = Field(ge=1)
    markdown_path: str | None = None
    pdf_path: str | None = None
    text_path: str | None = None
    skills_featured: list[str] = Field(default_factory=list)
    profile_bullet_ids: list[int] = Field(default_factory=list)


def insert_application(conn: sqlite3.Connection, application: Application) -> int:
    """Persist one application (and its skills/bullet-source links). Returns its new id."""
    with conn:
        cursor = conn.execute(
            """
            INSERT INTO applications
                (application_date, company, country, area, role_title, source, ingestion_tier,
                 match_score, output_language, page_count, markdown_path, pdf_path, text_path)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                application.application_date.isoformat(),
                application.company,
                application.country,
                application.area,
                application.role_title,
                application.source,
                application.ingestion_tier,
                application.match_score,
                application.output_language,
                application.page_count,
                application.markdown_path,
                application.pdf_path,
                application.text_path,
            ),
        )
        application_id = cursor.lastrowid

        conn.executemany(
            "INSERT INTO application_skills (application_id, skill_name) VALUES (?, ?)",
            [(application_id, skill) for skill in application.skills_featured],
        )
        conn.executemany(
            """
            INSERT INTO application_bullet_sources (application_id, profile_bullet_id)
            VALUES (?, ?)
            """,
            [(application_id, bullet_id) for bullet_id in application.profile_bullet_ids],
        )

    return application_id


def list_applications(
    conn: sqlite3.Connection,
    *,
    company: str | None = None,
    country: str | None = None,
    area: str | None = None,
    skill: str | None = None,
    sort_by: str = "application_date",
    descending: bool = True,
) -> list[Application]:
    """List applications, combining any of the given filters with AND (criterion 30)."""
    if sort_by not in _SORTABLE_COLUMNS:
        raise ValueError(f"cannot sort by {sort_by!r} — choose one of {sorted(_SORTABLE_COLUMNS)}")

    clauses = []
    params: list[str] = []
    joins = ""
    if company is not None:
        clauses.append("a.company = ?")
        params.append(company)
    if country is not None:
        clauses.append("a.country = ?")
        params.append(country)
    if area is not None:
        clauses.append("a.area = ?")
        params.append(area)
    if skill is not None:
        joins = "JOIN application_skills sk ON sk.application_id = a.id"
        clauses.append("sk.skill_name = ?")
        params.append(skill)

    where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
    order_column = _SORTABLE_COLUMNS[sort_by]
    order_direction = "DESC" if descending else "ASC"

    rows = conn.execute(
        f"""
        SELECT DISTINCT a.*
        FROM applications a
        {joins}
        {where}
        ORDER BY a.{order_column} {order_direction}, a.id {order_direction}
        """,  # noqa: S608 — joins/where/order pieces are built only from the whitelist above
        params,
    ).fetchall()

    return [_row_to_application(conn, row) for row in rows]


def _row_to_application(conn: sqlite3.Connection, row: sqlite3.Row) -> Application:
    skills = [
        r["skill_name"]
        for r in conn.execute(
            "SELECT skill_name FROM application_skills WHERE application_id = ? "
            "ORDER BY skill_name",
            (row["id"],),
        )
    ]
    bullet_ids = [
        r["profile_bullet_id"]
        for r in conn.execute(
            """
            SELECT profile_bullet_id FROM application_bullet_sources
            WHERE application_id = ? ORDER BY profile_bullet_id
            """,
            (row["id"],),
        )
    ]
    return Application(
        id=row["id"],
        application_date=row["application_date"],
        company=row["company"],
        country=row["country"],
        area=row["area"],
        role_title=row["role_title"],
        source=row["source"],
        ingestion_tier=row["ingestion_tier"],
        match_score=row["match_score"],
        output_language=row["output_language"],
        page_count=row["page_count"],
        markdown_path=row["markdown_path"],
        pdf_path=row["pdf_path"],
        text_path=row["text_path"],
        skills_featured=skills,
        profile_bullet_ids=bullet_ids,
    )
