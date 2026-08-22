"""AC-006 / contract C-010: when a user submits a generation request for a refused language
through the web UI, the HTTP response reports the refusal (422) with the reason text visible
in the response body -- draft.html.jinja's `generation_failure.reason` block, exercised here
for the first time on this path -- rather than an unhandled 500.

Uses FastAPI's TestClient, which drives the ASGI app in-process without binding a socket --
pattern from tests/unit/web/test_download_guard.py.
"""

from __future__ import annotations

from datetime import datetime, timezone

from fastapi.testclient import TestClient

from cv_writer.generation.rephraser import FakeRephraser
from cv_writer.ingestion.models import Posting
from cv_writer.web.app import create_app


def _app_and_draft_id(tmp_path):
    # French: a language a shipped profile can genuinely name (unlike "unknown"), but never
    # in SUPPORTED_LANGUAGES -- so the refusal is reachable through the SUPPORTED_LANGUAGES
    # gate even though the profile itself would otherwise permit it at "professional".
    profile_path = tmp_path / "profile.yaml"
    profile_path.write_text(
        "identity:\n  name: Ana Example\n  email: ana@example.com\n"
        "languages:\n  - name: French\n    proficiency: professional\n"
        "job_histories: []\nskills: []\n",
        encoding="utf-8",
    )
    app = create_app(
        profile_path=profile_path,
        db_path=tmp_path / "cv.sqlite3",
        output_dir=tmp_path / "applications",
        rephraser=FakeRephraser(),
    )
    posting = Posting(
        raw_text="We are hiring a backend engineer.",
        source="pasted",
        fetched_at=datetime.now(timezone.utc),
        ingestion_tier=3,
    )
    draft = app.state.draft_store.create(
        posting=posting,
        company="Acme Corp",
        country="France",
        area="Engineering",
        role_title="Backend Engineer",
    )
    return app, draft.id


def test_a_refused_language_reaches_the_user_as_a_422_with_the_reason_visible(tmp_path):
    app, draft_id = _app_and_draft_id(tmp_path)

    response = TestClient(app).post(
        f"/drafts/{draft_id}/generate",
        data={"language_override": "french"},
    )

    assert response.status_code == 422
    assert "not a language this tool can generate a CV in" in response.text
