"""Criterion 21 (via POST /drafts, the URL-ingestion route): ingest_from_url() always returns a
Posting with company/role_title/country unset — Posting's own docstring documents them as "left
optional here... may be filled in later for a fetched one". create_draft_from_url() is that
later point. Before this fix it filled them in only on the Draft, never on draft.posting itself,
which meant generation/language.py::_resolve_pt_variant() — which reads posting.country, not
Draft.country — always saw None for a URL-ingested posting and fell back to BR-lexis sniffing
instead of resolving Portugal/Angola/Mozambique/... straight to pt-pt. The paste route
(create_draft_from_paste -> ingest_pasted()) never had this gap, since ingest_pasted() takes
country directly and puts it on the Posting it builds.

Uses FastAPI's TestClient, which drives the ASGI app in-process without binding a socket — not
"starting a web server" in the sense criterion 34 rules out for tests of the domain core (this
test is for the UI layer's own wiring), matching tests/unit/web/test_download_guard.py's own
justification for the same pattern.
"""

from __future__ import annotations

from datetime import datetime, timezone

from fastapi.testclient import TestClient

from cv_writer.generation.language import resolve_output_language
from cv_writer.ingestion.models import Posting
from cv_writer.profile.loader import load_profile
from cv_writer.web.app import create_app


def _stub_ingest_url(url: str, **_kwargs) -> Posting:
    # A stand-in for ingest_from_url() that returns exactly what tier 1/2 actually produce —
    # company/role_title/country all unset, per ingestion/pipeline.py's own _posting().
    return Posting(
        raw_text="Estamos a contratar um Engenheiro de Backend.",
        source=url,
        fetched_at=datetime.now(timezone.utc),
        ingestion_tier=1,
    )


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
        ingest_url=_stub_ingest_url,
    )


def test_the_confirmed_country_lands_on_the_draft_postings_own_country_field(tmp_path):
    app = _app(tmp_path)
    client = TestClient(app, follow_redirects=False)

    response = client.post(
        "/drafts",
        data={
            "url": "https://example.com/job",
            "company": "Acme Corp",
            "country": "Portugal",
            "area": "Engineering",
            "role_title": "Backend Engineer",
        },
    )

    draft_id = response.headers["location"].removeprefix("/drafts/")
    draft = app.state.draft_store.get(draft_id)
    assert draft.posting.country == "Portugal"


def test_the_confirmed_company_and_role_title_also_land_on_the_draft_postings_own_fields(
    tmp_path,
):
    app = _app(tmp_path)
    client = TestClient(app, follow_redirects=False)

    response = client.post(
        "/drafts",
        data={
            "url": "https://example.com/job",
            "company": "Acme Corp",
            "country": "Portugal",
            "area": "Engineering",
            "role_title": "Backend Engineer",
        },
    )

    draft_id = response.headers["location"].removeprefix("/drafts/")
    draft = app.state.draft_store.get(draft_id)
    assert draft.posting.company == "Acme Corp"
    assert draft.posting.role_title == "Backend Engineer"


def test_the_filled_in_country_makes_pt_pt_variant_resolution_actually_fire(tmp_path):
    # The concrete downstream effect of the plumbing fix above: without posting.country set,
    # resolve_output_language() has no country signal and falls back to BR-lexis sniffing,
    # which a short, lexis-free Portuguese posting like this one would never trip — it would
    # resolve variant=None and generate_cv() would never run the PT-PT brasileirismos check
    # (criterion 21) at all.
    app = _app(tmp_path)
    client = TestClient(app, follow_redirects=False)
    response = client.post(
        "/drafts",
        data={
            "url": "https://example.com/job",
            "company": "Acme Corp",
            "country": "Portugal",
            "area": "Engineering",
            "role_title": "Backend Engineer",
        },
    )
    draft_id = response.headers["location"].removeprefix("/drafts/")
    draft = app.state.draft_store.get(draft_id)
    profile = load_profile(app.state.profile_path)

    resolution = resolve_output_language(draft.posting, profile, override="portuguese")

    assert resolution.variant == "pt-pt"
