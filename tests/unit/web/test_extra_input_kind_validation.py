"""Criterion 17 (POST /drafts/{id}/inputs): `kind` only ever reaches the fixed `<select>`
options in draft.html.jinja in normal browser use, but it arrives as a plain form string —
a hand-crafted request can send a value outside `ExtraInputKind`, which used to raise an
uncaught `ValueError` (`ExtraInputKind(kind)`) straight into Starlette's default 500 handler.
That's the same class of bug the review flagged for an unwhitelisted `sort_by` on
GET /applications (tests/e2e/test_ui_track_record.py); this asserts the analogous fix here.

Uses FastAPI's TestClient, which drives the ASGI app in-process without binding a socket —
not "starting a web server" in the sense criterion 34 rules out for tests of the domain core
(this test is for the UI layer itself), matching tests/unit/web/test_download_guard.py's own
justification for the same pattern.
"""

from __future__ import annotations

from datetime import datetime, timezone

from fastapi.testclient import TestClient

from cv_writer.ingestion.models import Posting
from cv_writer.web.app import create_app


def _app_and_draft_id(tmp_path):
    profile_path = tmp_path / "profile.yaml"
    profile_path.write_text(
        "identity:\n  name: Ana Example\n  email: ana@example.com\n"
        "languages: []\njob_histories: []\nskills: []\n",
        encoding="utf-8",
    )
    app = create_app(
        profile_path=profile_path,
        db_path=tmp_path / "cv.sqlite3",
        output_dir=tmp_path / "applications",
    )
    posting = Posting(
        raw_text="We are hiring a backend engineer.",
        source="pasted",
        fetched_at=datetime.now(timezone.utc),
        ingestion_tier=3,
    )
    draft = app.state.draft_store.create(
        posting=posting, company="Acme Corp", country="Portugal", area="Engineering",
        role_title="Backend Engineer",
    )
    return app, draft.id


def test_an_unwhitelisted_extra_input_kind_renders_an_error_not_a_500(tmp_path):
    app, draft_id = _app_and_draft_id(tmp_path)

    response = TestClient(app).post(
        f"/drafts/{draft_id}/inputs",
        data={"kind": "not_a_real_kind", "text": "some text"},
    )

    assert response.status_code == 422
    assert "unknown extra-input kind" in response.text.lower()


def test_an_unwhitelisted_extra_input_kind_does_not_append_to_the_draft(tmp_path):
    app, draft_id = _app_and_draft_id(tmp_path)

    TestClient(app).post(
        f"/drafts/{draft_id}/inputs",
        data={"kind": "not_a_real_kind", "text": "some text"},
    )

    assert app.state.draft_store.get(draft_id).extra_inputs == []


def test_a_whitelisted_extra_input_kind_still_redirects_and_is_appended(tmp_path):
    app, draft_id = _app_and_draft_id(tmp_path)

    response = TestClient(app).post(
        f"/drafts/{draft_id}/inputs",
        data={"kind": "achievement", "text": "Shipped a thing."},
        follow_redirects=False,
    )

    assert response.status_code == 303
    assert app.state.draft_store.get(draft_id).extra_inputs[0].text == "Shipped a thing."
