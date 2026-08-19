"""ADR 0005 decision 5: the web layer's Jinja environment has autoescaping on, and no template
uses `|safe` on user-controlled data — company/role/country/area and extra-input text are all
user-supplied (posting text ultimately is too, via ingestion). This was checked by hand while
building the templates (see pairing/sessions/2026-08-18-slice5-web-ui-ci.md's "Learned" section,
which explicitly flags the absence of a test for it as a gap worth closing), but nothing in the
suite proved it mechanically until this test.

Uses FastAPI's TestClient, which drives the ASGI app in-process without binding a socket — not
"starting a web server" in the sense criterion 34 rules out for tests of the domain core (this
test is for the UI layer itself), matching tests/unit/web/test_download_guard.py's own
justification for the same pattern.
"""

from __future__ import annotations

from datetime import datetime, timezone

from fastapi.testclient import TestClient

from cv_writer.ingestion.models import Posting
from cv_writer.web.app import create_app

_INJECTION = "<script>alert('xss')</script>"


def _app(tmp_path):
    profile_path = tmp_path / "profile.yaml"
    profile_path.write_text(
        "identity:\n  name: Ana Example\n  email: ana@example.com\n"
        "languages: []\njob_histories: []\nskills: []\n",
        encoding="utf-8",
    )
    return create_app(
        profile_path=profile_path,
        db_path=tmp_path / "cv.sqlite3",
        output_dir=tmp_path / "applications",
    )


def test_a_company_name_containing_html_metacharacters_is_escaped_on_the_draft_page(tmp_path):
    app = _app(tmp_path)
    posting = Posting(
        raw_text="We are hiring a backend engineer.",
        source="pasted",
        fetched_at=datetime.now(timezone.utc),
        ingestion_tier=3,
    )
    draft = app.state.draft_store.create(
        posting=posting, company=_INJECTION, country="Portugal", area="Engineering",
        role_title="Backend Engineer",
    )

    response = TestClient(app).get(f"/drafts/{draft.id}")

    assert response.status_code == 200
    assert _INJECTION not in response.text
    assert "&lt;script&gt;" in response.text


def test_extra_input_text_containing_html_metacharacters_is_escaped_on_the_draft_page(tmp_path):
    app = _app(tmp_path)
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
    client = TestClient(app)
    client.post(
        f"/drafts/{draft.id}/inputs",
        data={"kind": "achievement", "text": _INJECTION},
        follow_redirects=False,
    )

    response = client.get(f"/drafts/{draft.id}")

    assert response.status_code == 200
    assert _INJECTION not in response.text
    assert "&lt;script&gt;" in response.text
