"""Criterion 33 (-> criterion 30): the track record browser supports the same combined
filtering and sorting as list_applications() — driven through the UI's own GET /applications
route (the db-layer behavior itself is already covered by
tests/integration/db/test_track_record.py; this proves the route wires it through correctly,
including the "bad sort_by renders an error, not a 500" case ADR 0005's route table calls out).
"""

from __future__ import annotations

from datetime import date

from fastapi.testclient import TestClient

from cv_writer.db import Application, connect, insert_application
from cv_writer.web.app import create_app


def _client(tmp_path, profile_path) -> TestClient:
    app = create_app(
        profile_path=profile_path,
        db_path=tmp_path / "cv.sqlite3",
        output_dir=tmp_path / "applications",
    )
    return TestClient(app)


def _seed(tmp_path, **overrides) -> None:
    conn = connect(tmp_path / "cv.sqlite3")
    fields = dict(
        application_date=date(2026, 1, 1),
        company="Acme",
        country="Portugal",
        area="Engineering",
        role_title="Backend Engineer",
        source="pasted",
        output_language="english",
        page_count=1,
        skills_featured=[],
    )
    fields.update(overrides)
    insert_application(conn, Application(**fields))


def test_combined_skill_and_country_filters_show_only_the_overlapping_rows(tmp_path, profile_path):
    _seed(
        tmp_path,
        company="Acme",
        country="Portugal",
        skills_featured=["Python"],
        application_date=date(2026, 1, 5),
    )
    _seed(
        tmp_path,
        company="Globex",
        country="Portugal",
        skills_featured=["Python", "Go"],
        application_date=date(2026, 2, 1),
    )
    _seed(
        tmp_path,
        company="Initech",
        country="Germany",
        skills_featured=["Python"],
        application_date=date(2026, 3, 1),
    )
    _seed(
        tmp_path,
        company="Umbrella",
        country="Portugal",
        skills_featured=["Go"],
        application_date=date(2026, 4, 1),
    )

    response = _client(tmp_path, profile_path).get(
        "/applications", params={"skill": "Python", "country": "Portugal"}
    )

    assert response.status_code == 200
    assert "Globex" in response.text
    assert "Acme" in response.text
    assert "Initech" not in response.text
    assert "Umbrella" not in response.text


def test_sort_by_date_ascending_orders_oldest_first(tmp_path, profile_path):
    _seed(tmp_path, company="Newer", application_date=date(2026, 3, 1))
    _seed(tmp_path, company="Older", application_date=date(2026, 1, 1))

    response = _client(tmp_path, profile_path).get(
        "/applications", params={"sort_by": "date", "descending": "false"}
    )

    assert response.status_code == 200
    assert response.text.index("Older") < response.text.index("Newer")


def test_an_unwhitelisted_sort_by_renders_an_error_not_a_500(tmp_path, profile_path):
    _seed(tmp_path, company="Acme")

    # "skill" is a filter only, never a sort option (list_applications()'s own whitelist) —
    # the route must turn that ValueError into a 200 with an error banner, not a 500.
    response = _client(tmp_path, profile_path).get("/applications", params={"sort_by": "skill"})

    assert response.status_code == 200
    assert "cannot sort by" in response.text.lower()
