"""Criteria 9.3, 11: when URL ingestion fails (tier 1 and tier 2 both), the paste fallback is
offered with the reason — never a silent empty result — and pasting the same posting afterward
still succeeds and reaches a draft.
"""

from __future__ import annotations

from fastapi.testclient import TestClient

from cv_writer.generation.rephraser import FakeRephraser
from cv_writer.ingestion.models import IngestionFailure
from cv_writer.web.app import create_app


def _failing_ingest_url(url: str, **_kwargs) -> IngestionFailure:
    return IngestionFailure(
        tier_attempted=2,
        reason="tier 1 failed (HTTP 403); tier 2 also failed (login wall detected)",
    )


def _client(tmp_path, profile_path) -> TestClient:
    app = create_app(
        profile_path=profile_path,
        db_path=tmp_path / "cv.sqlite3",
        output_dir=tmp_path / "applications",
        rephraser=FakeRephraser(),
        ingest_url=_failing_ingest_url,
    )
    return TestClient(app)


def _url_form(**overrides) -> dict:
    fields = {
        "url": "https://example.com/blocked-job",
        "company": "Acme Corp",
        "country": "Portugal",
        "area": "Engineering",
        "role_title": "Backend Engineer",
    }
    fields.update(overrides)
    return fields


def test_url_ingestion_failure_shows_the_reason_and_offers_the_paste_fallback(
    tmp_path, profile_path
):
    response = _client(tmp_path, profile_path).post("/drafts", data=_url_form())

    assert response.status_code == 422
    assert "login wall detected" in response.text
    assert "paste" in response.text.lower()
    # The fields the user already typed aren't thrown away.
    assert "Acme Corp" in response.text


def test_pasting_after_a_url_failure_still_reaches_a_draft(tmp_path, profile_path):
    client = _client(tmp_path, profile_path)

    failed = client.post("/drafts", data=_url_form())
    assert failed.status_code == 422

    pasted = client.post(
        "/drafts/paste",
        data={
            "text": "We need a backend engineer with strong Python experience.",
            "company": "Acme Corp",
            "country": "Portugal",
            "area": "Engineering",
            "role_title": "Backend Engineer",
        },
        follow_redirects=False,
    )

    assert pasted.status_code == 303
    assert pasted.headers["location"].startswith("/drafts/")
