"""Criteria 29-31: every generated application is persisted in the embedded SQLite database
with date, company, country, area/department, role title, source URL or 'pasted', ingestion
tier, match score, output language, page count, skills featured, artifact paths, and the
profile-bullet ids used (29). The track record can be listed, sorted, and filtered by date,
company, country, area, and skill, including combined filters (30). The DB file lives outside
version control, its location is configurable, and a fresh run against a missing DB creates and
migrates it without manual steps (31).

No generation pipeline exists yet (that's slice 4) — these tests exercise persistence and
querying directly against constructed Application records, per the spec's own slice ordering
("Database + track record ... still headless").
"""

from datetime import date
from pathlib import Path

from cv_writer.db import (
    Application,
    connect,
    get_application,
    insert_application,
    list_applications,
)


def _application(**overrides) -> Application:
    defaults = dict(
        application_date=date(2026, 1, 10),
        company="Acme Corp",
        country="Portugal",
        area="Engineering",
        role_title="Backend Engineer",
        source="https://example.com/jobs/123",
        ingestion_tier=1,
        match_score=0.82,
        output_language="en",
        page_count=1,
        markdown_path="output/2026-01-10-acme-backend-engineer.md",
        pdf_path="output/2026-01-10-acme-backend-engineer.pdf",
        text_path="output/2026-01-10-acme-backend-engineer.txt",
        skills_featured=["Python", "SQL"],
        profile_bullet_ids=["job-acme-2020-b1", "job-acme-2020-b2", "job-acme-2020-b3"],
    )
    defaults.update(overrides)
    return Application(**defaults)


def test_missing_db_file_is_created_and_migrated_automatically(tmp_path):
    db_path = tmp_path / "nested" / "cv_writer.sqlite3"
    assert not db_path.exists()

    conn = connect(db_path)

    assert db_path.exists()
    # Schema is in place — querying the track record table doesn't raise.
    assert conn.execute("SELECT COUNT(*) FROM applications").fetchone()[0] == 0


def test_db_path_is_configurable_via_env_var(tmp_path, monkeypatch):
    db_path = tmp_path / "custom" / "cv.sqlite3"
    monkeypatch.setenv("CV_WRITER_DB_PATH", str(db_path))

    conn = connect()

    assert db_path.exists()
    conn.execute("SELECT 1")


def test_db_path_defaults_outside_version_control(monkeypatch):
    monkeypatch.delenv("CV_WRITER_DB_PATH", raising=False)

    from cv_writer.db.connection import get_db_path

    default_path = get_db_path()

    # data/ is gitignored wholesale except the example profile (see .gitignore) —
    # the default location must land there, not somewhere src/tests would pick it up.
    assert Path("data") in default_path.parents or default_path.parent == Path("data")


def test_insert_application_persists_all_required_fields(tmp_path):
    conn = connect(tmp_path / "cv.sqlite3")
    app = _application()

    app_id = insert_application(conn, app)

    row = conn.execute("SELECT * FROM applications WHERE id = ?", (app_id,)).fetchone()
    assert row["company"] == "Acme Corp"
    assert row["country"] == "Portugal"
    assert row["area"] == "Engineering"
    assert row["role_title"] == "Backend Engineer"
    assert row["source"] == "https://example.com/jobs/123"
    assert row["ingestion_tier"] == 1
    assert row["match_score"] == 0.82
    assert row["output_language"] == "en"
    assert row["page_count"] == 1
    assert row["markdown_path"] == "output/2026-01-10-acme-backend-engineer.md"

    skills = {
        r["skill_name"]
        for r in conn.execute(
            "SELECT skill_name FROM application_skills WHERE application_id = ?", (app_id,)
        )
    }
    assert skills == {"Python", "SQL"}

    bullet_ids = {
        r["profile_bullet_id"]
        for r in conn.execute(
            "SELECT profile_bullet_id FROM application_bullet_sources WHERE application_id = ?",
            (app_id,),
        )
    }
    assert bullet_ids == {"job-acme-2020-b1", "job-acme-2020-b2", "job-acme-2020-b3"}


def test_insert_application_accepts_pasted_source_and_missing_tier(tmp_path):
    conn = connect(tmp_path / "cv.sqlite3")
    app = _application(source="pasted", ingestion_tier=None)

    app_id = insert_application(conn, app)

    row = conn.execute(
        "SELECT source, ingestion_tier FROM applications WHERE id = ?", (app_id,)
    ).fetchone()
    assert row["source"] == "pasted"
    assert row["ingestion_tier"] is None


def test_list_applications_round_trips_through_the_model(tmp_path):
    conn = connect(tmp_path / "cv.sqlite3")
    insert_application(conn, _application())

    [listed] = list_applications(conn)

    assert listed.company == "Acme Corp"
    assert listed.application_date == date(2026, 1, 10)
    assert listed.skills_featured == ["Python", "SQL"]
    assert listed.profile_bullet_ids == ["job-acme-2020-b1", "job-acme-2020-b2", "job-acme-2020-b3"]
    assert listed.id is not None


def test_list_applications_filters_by_country_and_skill_combined_sorted_by_date_desc(tmp_path):
    conn = connect(tmp_path / "cv.sqlite3")
    insert_application(
        conn,
        _application(
            company="Acme",
            country="Portugal",
            application_date=date(2026, 1, 5),
            skills_featured=["Python"],
        ),
    )
    insert_application(
        conn,
        _application(
            company="Globex",
            country="Portugal",
            application_date=date(2026, 2, 1),
            skills_featured=["Python", "Go"],
        ),
    )
    insert_application(
        conn,
        _application(
            company="Initech",
            country="Germany",
            application_date=date(2026, 3, 1),
            skills_featured=["Python"],
        ),
    )
    insert_application(
        conn,
        _application(
            company="Umbrella",
            country="Portugal",
            application_date=date(2026, 4, 1),
            skills_featured=["Go"],
        ),
    )

    results = list_applications(conn, country="Portugal", skill="Python")

    # Umbrella: wrong skill. Initech: wrong country. Globex/Acme: both match, newest first.
    assert [r.company for r in results] == ["Globex", "Acme"]


def test_list_applications_filters_by_company_and_area(tmp_path):
    conn = connect(tmp_path / "cv.sqlite3")
    insert_application(conn, _application(company="Acme", area="Engineering"))
    insert_application(conn, _application(company="Acme", area="Sales"))
    insert_application(conn, _application(company="Globex", area="Engineering"))

    results = list_applications(conn, company="Acme", area="Engineering")

    assert len(results) == 1
    assert results[0].area == "Engineering"


def test_get_application_returns_the_application_with_the_given_id(tmp_path):
    conn = connect(tmp_path / "cv.sqlite3")
    app_id = insert_application(conn, _application(company="Acme"))

    found = get_application(conn, app_id)

    assert found is not None
    assert found.id == app_id
    assert found.company == "Acme"
    assert found.skills_featured == ["Python", "SQL"]


def test_get_application_returns_none_for_an_id_that_does_not_exist(tmp_path):
    conn = connect(tmp_path / "cv.sqlite3")

    assert get_application(conn, 999) is None


def test_list_applications_sorts_ascending_by_date_when_requested(tmp_path):
    conn = connect(tmp_path / "cv.sqlite3")
    insert_application(conn, _application(company="A", application_date=date(2026, 3, 1)))
    insert_application(conn, _application(company="B", application_date=date(2026, 1, 1)))

    results = list_applications(conn, descending=False)

    assert [r.company for r in results] == ["B", "A"]
