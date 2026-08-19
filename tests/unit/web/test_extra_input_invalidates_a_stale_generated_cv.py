"""POST /drafts/{id}/inputs: adding extra input after a CV was already generated for the draft
used to leave draft.generated_cv/page_fit untouched. /drafts/{id}/pages and
/drafts/{id}/confirm only ever check `generated_cv is None`, so a stale CV computed *before*
the new input could still be paged through and confirmed — silently shipping an application
that doesn't include the input the human just added, with no warning anywhere in the UI. This
proves the new input clears the stale CV, forcing a fresh /generate before either of those
routes will proceed.

Builds the "already generated" state directly on the DraftStore rather than by actually POSTing
to /drafts/{id}/generate, so this test doesn't need real Chromium — matching
tests/unit/web/test_draft_store.py's own posture of driving the store directly for state setup.
Uses FastAPI's TestClient for the route call itself, which drives the ASGI app in-process
without binding a socket (see test_download_guard.py's justification for the same pattern).
"""

from __future__ import annotations

from datetime import datetime, timezone

from fastapi.testclient import TestClient

from cv_writer.generation.models import GeneratedBulletDraft, GeneratedCv
from cv_writer.generation.page_fit import PageFitResult
from cv_writer.ingestion.models import Posting
from cv_writer.web.app import create_app


def _app_and_generated_draft_id(tmp_path):
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
    draft.generated_cv = GeneratedCv(
        markdown="- Cut latency by 77%.",
        language="english",
        variant=None,
        source_ids_used=["job-acme-b1"],
        accepted_bullets=[
            GeneratedBulletDraft(text="Cut latency by 77%.", source_id="job-acme-b1")
        ],
    )
    draft.page_fit = PageFitResult(
        fitted_source_ids=["job-acme-b1"],
        dropped_source_ids=[],
        page_count=1,
        achieved_one_page=True,
    )
    app.state.draft_store.update(draft)
    return app, draft.id


def test_adding_extra_input_after_generation_clears_the_stale_generated_cv(tmp_path):
    app, draft_id = _app_and_generated_draft_id(tmp_path)

    TestClient(app).post(
        f"/drafts/{draft_id}/inputs",
        data={"kind": "achievement", "text": "Led a zero-downtime migration."},
    )

    draft = app.state.draft_store.get(draft_id)
    assert draft.generated_cv is None
    assert draft.page_fit is None


def test_the_page_choice_route_409s_instead_of_showing_the_stale_page_fit_after_new_input(
    tmp_path,
):
    app, draft_id = _app_and_generated_draft_id(tmp_path)
    client = TestClient(app)
    client.post(
        f"/drafts/{draft_id}/inputs",
        data={"kind": "achievement", "text": "Led a zero-downtime migration."},
    )

    response = client.get(f"/drafts/{draft_id}/pages")

    assert response.status_code == 409


def test_adding_extra_input_before_any_generation_does_not_error(tmp_path):
    # generated_cv/page_fit are already None pre-generation — the clearing logic must be a
    # no-op then, not something that only works once a CV exists.
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

    response = TestClient(app).post(
        f"/drafts/{draft.id}/inputs",
        data={"kind": "achievement", "text": "Led a zero-downtime migration."},
        follow_redirects=False,
    )

    assert response.status_code == 303
    assert app.state.draft_store.get(draft.id).generated_cv is None
