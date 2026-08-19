"""ADR 0005 decision 7: GET /applications/{id}/download/{kind} only ever serves a file whose
resolved path sits inside the resolved output directory, re-checked at request time — not
merely trusted because build_output_paths()'s slugging makes a traversal-shaped company name
unlikely to ever reach a stored path in practice. Uses FastAPI's TestClient, which drives the
ASGI app in-process without binding a socket — not "starting a web server" in the sense
criterion 34 rules out for tests of the domain core (this test is for the UI layer itself).
"""

from __future__ import annotations

from fastapi.testclient import TestClient

from cv_writer.db import Application, connect, insert_application
from cv_writer.web.app import create_app


def _app_and_output_dir(tmp_path):
    output_dir = tmp_path / "applications"
    output_dir.mkdir()
    app = create_app(db_path=tmp_path / "cv.sqlite3", output_dir=output_dir)
    return app, output_dir


def _insert(tmp_path, **overrides) -> int:
    conn = connect(tmp_path / "cv.sqlite3")
    fields = dict(
        application_date="2026-01-10",
        company="Acme Corp",
        country="Portugal",
        area="Engineering",
        role_title="Backend Engineer",
        source="pasted",
        output_language="english",
        page_count=1,
    )
    fields.update(overrides)
    return insert_application(conn, Application(**fields))


def test_download_404s_when_the_stored_path_escapes_the_output_directory(tmp_path):
    app, _output_dir = _app_and_output_dir(tmp_path)
    outside_file = tmp_path / "secret.txt"
    outside_file.write_text("not yours", encoding="utf-8")
    application_id = _insert(tmp_path, markdown_path=str(outside_file))

    response = TestClient(app).get(f"/applications/{application_id}/download/markdown")

    assert response.status_code == 404


def test_download_serves_a_file_that_really_is_inside_the_output_directory(tmp_path):
    app, output_dir = _app_and_output_dir(tmp_path)
    inside_file = output_dir / "2026-01-10-acme-corp-backend-engineer.md"
    inside_file.write_text("# Ana Example", encoding="utf-8")
    application_id = _insert(tmp_path, markdown_path=str(inside_file))

    response = TestClient(app).get(f"/applications/{application_id}/download/markdown")

    assert response.status_code == 200
    assert "Ana Example" in response.text


def test_download_404s_for_an_unwhitelisted_artifact_kind(tmp_path):
    app, output_dir = _app_and_output_dir(tmp_path)
    inside_file = output_dir / "cv.md"
    inside_file.write_text("content", encoding="utf-8")
    application_id = _insert(tmp_path, markdown_path=str(inside_file))

    response = TestClient(app).get(f"/applications/{application_id}/download/docx")

    assert response.status_code == 404


def test_download_404s_when_the_application_id_does_not_exist(tmp_path):
    app, _output_dir = _app_and_output_dir(tmp_path)

    response = TestClient(app).get("/applications/999/download/markdown")

    assert response.status_code == 404


def test_download_404s_when_the_application_has_no_path_of_that_kind(tmp_path):
    app, _output_dir = _app_and_output_dir(tmp_path)
    application_id = _insert(tmp_path, markdown_path=None)

    response = TestClient(app).get(f"/applications/{application_id}/download/markdown")

    assert response.status_code == 404
