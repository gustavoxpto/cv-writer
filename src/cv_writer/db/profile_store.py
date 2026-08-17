"""Load a validated Profile into the database (spec criterion 6).

The database copy is a **derived, rebuildable projection** of data/profile.yaml — it is never
edited independently (spec open question 3: YAML stays the only write path). That framing is
what makes idempotency simple: rather than diffing and upserting row by row, every call clears
the profile-derived tables and reinserts from the in-memory Profile, inside one transaction, so
a load either fully replaces the previous snapshot or (on error) leaves it untouched — never a
partial rebuild.

Track-record tables (applications, ...) are untouched here; see track_record.py.
"""

from __future__ import annotations

import json
import sqlite3
from datetime import date

from ..profile import Profile

# Order matters: children before parents, respecting the foreign keys in migrations/0001_init.sql.
_PROFILE_TABLES_CHILD_FIRST = (
    "skill_evidence",
    "skills",
    "bullets",
    "job_histories",
    "education",
    "languages",
    "identity",
)


def load_profile_into_db(profile: Profile, conn: sqlite3.Connection) -> None:
    """Replace the DB's profile-derived tables with the contents of `profile`."""
    with conn:
        _clear_profile_tables(conn)
        _insert_identity(conn, profile)
        _insert_languages(conn, profile)
        _insert_education(conn, profile)
        history_ids = _insert_job_histories_and_bullets(conn, profile)
        _insert_skills_and_evidence(conn, profile, history_ids)


def _clear_profile_tables(conn: sqlite3.Connection) -> None:
    for table in _PROFILE_TABLES_CHILD_FIRST:
        conn.execute(f"DELETE FROM {table}")  # noqa: S608 — table names are our own constant tuple


def _insert_identity(conn: sqlite3.Connection, profile: Profile) -> None:
    identity = profile.identity
    conn.execute(
        """
        INSERT INTO identity (id, name, email, phone, location, links_json)
        VALUES (1, ?, ?, ?, ?, ?)
        """,
        (
            identity.name,
            identity.email,
            identity.phone,
            identity.location,
            json.dumps(identity.links),
        ),
    )


def _insert_languages(conn: sqlite3.Connection, profile: Profile) -> None:
    conn.executemany(
        "INSERT INTO languages (name, proficiency) VALUES (?, ?)",
        [(lang.name, lang.proficiency) for lang in profile.languages],
    )


def _insert_education(conn: sqlite3.Connection, profile: Profile) -> None:
    conn.executemany(
        """
        INSERT INTO education (institution, degree, field, start_date, end_date)
        VALUES (?, ?, ?, ?, ?)
        """,
        [
            (
                edu.institution,
                edu.degree,
                edu.field,
                _date_str(edu.start_date),
                _date_str(edu.end_date),
            )
            for edu in profile.education
        ],
    )


def _insert_job_histories_and_bullets(conn: sqlite3.Connection, profile: Profile) -> set[str]:
    history_ids: set[str] = set()
    for history in profile.job_histories:
        conn.execute(
            """
            INSERT INTO job_histories (id, company, role_title, country, area, start_date, end_date)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                history.id,
                history.company,
                history.role_title,
                history.country,
                history.area,
                _date_str(history.start_date),
                _date_str(history.end_date),
            ),
        )
        history_ids.add(history.id)

        for position, bullet in enumerate(history.bullets):
            metric = bullet.metric
            conn.execute(
                """
                INSERT INTO bullets
                    (job_history_id, position, situation, task, action, result,
                     metric_value, metric_unit, metric_baseline)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    history.id,
                    position,
                    bullet.situation,
                    bullet.task,
                    bullet.action,
                    bullet.result,
                    metric.value if metric else None,
                    metric.unit if metric else None,
                    metric.baseline if metric else None,
                ),
            )
    return history_ids


def _insert_skills_and_evidence(
    conn: sqlite3.Connection, profile: Profile, history_ids: set[str]
) -> None:
    for skill in profile.skills:
        cursor = conn.execute(
            "INSERT INTO skills (name, category, level, years) VALUES (?, ?, ?, ?)",
            (skill.name, skill.category, skill.level, skill.years),
        )
        skill_id = cursor.lastrowid
        conn.executemany(
            "INSERT INTO skill_evidence (skill_id, job_history_id) VALUES (?, ?)",
            [(skill_id, history_id) for history_id in skill.evidence if history_id in history_ids],
        )


def _date_str(value: date | str | None) -> str | None:
    """`date` objects (and the literal string "present") both need to land as TEXT."""
    if value is None:
        return None
    if isinstance(value, date):
        return value.isoformat()
    return value
