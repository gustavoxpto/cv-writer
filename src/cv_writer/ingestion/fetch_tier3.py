"""Tier 3 ingestion: paste fallback (criterion 8).

No fetching, no escalation — the user has already supplied the text and the identifying
fields a URL fetch would otherwise leave blank. The only job here is to shape that input into
the same `Posting` model tiers 1/2 produce, so pasted and fetched postings are "otherwise
indistinguishable downstream" (criterion 8).

Unlike ingest_from_url() (pipeline.py), this raises ValueError on bad input rather than
returning a typed IngestionFailure. Deliberate, not an inconsistency to paper over: tiers 1/2
describe *external* outcomes (a fetch that failed for a reason worth showing the user), while
this is a direct call with arguments the caller controls — much closer to a constructor
rejecting bad input than to "the network/site did something." The eventual UI (slice 5) is
expected to validate its paste form before calling this, the same way it would validate any
other form.
"""

from __future__ import annotations

from datetime import datetime, timezone

from .models import PASTED_SOURCE, Posting


def ingest_pasted(
    text: str,
    *,
    company: str,
    role_title: str,
    country: str,
    fetched_at: datetime | None = None,
) -> Posting:
    """Build a Posting from pasted text plus the fields a URL fetch would have left implicit."""
    if not text.strip():
        raise ValueError("pasted posting text must not be empty")
    if not company.strip():
        raise ValueError("company must not be empty")
    if not role_title.strip():
        raise ValueError("role_title must not be empty")
    if not country.strip():
        raise ValueError("country must not be empty")

    return Posting(
        raw_text=text.strip(),
        source=PASTED_SOURCE,
        fetched_at=fetched_at or datetime.now(timezone.utc),
        ingestion_tier=3,
        company=company,
        role_title=role_title,
        country=country,
    )
