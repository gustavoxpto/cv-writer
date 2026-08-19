"""Criteria 32, 37: walk the full UI flow — posting -> match report -> extra input -> language
and page-count confirmation -> generate -> download the Markdown/PDF/text -> a real
track-record row — using FakeRephraser, exactly the walk criterion 37 asks for. TestClient
drives the ASGI app in-process (no bound socket); real Chromium still renders the PDF, same as
the generation-layer integration tests.
"""

from __future__ import annotations

from fastapi.testclient import TestClient

from cv_writer.generation.rephraser import FakeRephraser
from cv_writer.web.app import create_app

_POSTING_TEXT = """We are looking for a Senior Backend Engineer to join our growing team.

Requirements:
- Strong experience with Python
- Experience with Kubernetes
- SQL knowledge

Nice to have:
- Experience with AWS
"""


def _client(tmp_path, profile_path) -> TestClient:
    app = create_app(
        profile_path=profile_path,
        db_path=tmp_path / "cv.sqlite3",
        output_dir=tmp_path / "applications",
        rephraser=FakeRephraser(),
    )
    return TestClient(app)


def test_full_walk_from_pasted_posting_to_a_track_record_row(tmp_path, profile_path):
    client = _client(tmp_path, profile_path)

    draft_response = client.post(
        "/drafts/paste",
        data={
            "text": _POSTING_TEXT,
            "company": "Acme Corp",
            "country": "Portugal",
            "area": "Engineering",
            "role_title": "Backend Engineer",
        },
        follow_redirects=False,
    )
    assert draft_response.status_code == 303
    draft_url = draft_response.headers["location"]

    match_page = client.get(draft_url)
    assert match_page.status_code == 200
    assert "Match report" in match_page.text
    # Kubernetes has no evidencing history in the fixture profile — an explicit gap
    # (criterion 15), not a silently dropped requirement.
    assert "kubernetes" in match_page.text.lower()

    input_response = client.post(
        f"{draft_url}/inputs",
        data={
            "kind": "achievement",
            "text": "Led a zero-downtime Kubernetes migration for the checkout service.",
            "promote_candidate": "true",
        },
        follow_redirects=False,
    )
    assert input_response.status_code == 303

    draft_page_with_input = client.get(draft_url)
    assert "extra-1" in draft_page_with_input.text

    generate_response = client.post(
        f"{draft_url}/generate", data={"language_override": ""}, follow_redirects=False
    )
    assert generate_response.status_code == 303
    pages_url = generate_response.headers["location"]
    assert pages_url == f"{draft_url}/pages"

    pages_page = client.get(pages_url)
    assert pages_page.status_code == 200
    assert "page" in pages_page.text.lower()

    confirm_response = client.post(
        f"{draft_url}/confirm", data={"page_count": "1"}, follow_redirects=False
    )
    assert confirm_response.status_code == 303
    application_url = confirm_response.headers["location"]
    assert application_url.startswith("/applications/")

    application_page = client.get(application_url)
    assert application_page.status_code == 200
    assert "Acme Corp" in application_page.text

    for kind in ("markdown", "pdf", "text"):
        download = client.get(f"{application_url}/download/{kind}")
        assert download.status_code == 200
        assert len(download.content) > 0

    track_record_page = client.get("/applications")
    assert track_record_page.status_code == 200
    assert "Acme Corp" in track_record_page.text


def test_generation_failure_re_renders_the_draft_page_with_the_reason(tmp_path, profile_path):
    # A language the fixture profile has no working proficiency in at all (criterion 20's
    # refusal case) — walked through the UI, not just the pipeline directly, to prove the
    # route surfaces GenerationFailure instead of a 500.
    client = _client(tmp_path, profile_path)
    draft_response = client.post(
        "/drafts/paste",
        data={
            "text": "Wir suchen einen erfahrenen Softwareentwickler fuer unser Team.",
            "company": "Acme Corp",
            "country": "Germany",
            "area": "Engineering",
            "role_title": "Backend Engineer",
        },
        follow_redirects=False,
    )
    draft_url = draft_response.headers["location"]

    generate_response = client.post(f"{draft_url}/generate", data={"language_override": "german"})

    assert generate_response.status_code == 422
    assert "Generation failed" in generate_response.text
