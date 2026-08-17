"""Ingestion pipeline: escalate tier 1 -> tier 2, record which tier produced the posting, and
never proceed silently on thin or missing text (criteria 9, 11).

`ingest_from_url()` tries tier 1 first (fast path, criterion 9.1). If tier 1 fails for any
reason — non-200, request error, or too little extracted text — it escalates to tier 2
(criterion 9.2). If tier 2 also fails, the function returns an `IngestionFailure` naming why,
so the caller (eventually the UI) can offer the paste fallback (tier 3, criterion 9.3) with a
real reason instead of a silent empty result. Tier 3 is not called from here — it's invoked
directly by the caller once the user has that reason in hand (see fetch_tier3.ingest_pasted).
"""

from __future__ import annotations

from collections.abc import Callable
from datetime import datetime, timezone

from .fetch_tier1 import (
    DEFAULT_MIN_EXTRACTED_CHARS,
    DEFAULT_TIMEOUT_SECONDS,
    HttpResponse,
    default_http_get,
    fetch_tier1,
)
from .fetch_tier2 import DEFAULT_NAV_TIMEOUT_MS, Tier2Result, fetch_tier2
from .models import IngestionFailure, Posting


def ingest_from_url(
    url: str,
    *,
    http_get: Callable[[str, float], HttpResponse] = default_http_get,
    timeout: float = DEFAULT_TIMEOUT_SECONDS,
    nav_timeout_ms: int = DEFAULT_NAV_TIMEOUT_MS,
    min_chars: int = DEFAULT_MIN_EXTRACTED_CHARS,
    tier2_fetcher: Callable[..., Tier2Result] = fetch_tier2,
) -> Posting | IngestionFailure:
    tier1 = fetch_tier1(url, http_get=http_get, timeout=timeout, min_chars=min_chars)
    if tier1.ok:
        return _posting(url, tier1.extracted_text, tier=1)

    tier2 = tier2_fetcher(url, nav_timeout_ms=nav_timeout_ms, min_chars=min_chars)
    if tier2.ok:
        return _posting(url, tier2.extracted_text, tier=2)

    return IngestionFailure(
        tier_attempted=2,
        reason=f"tier 1 failed ({tier1.reason}); tier 2 also failed ({tier2.reason})",
    )


def _posting(url: str, text: str, *, tier: int) -> Posting:
    return Posting(
        raw_text=text,
        source=url,
        fetched_at=datetime.now(timezone.utc),
        ingestion_tier=tier,
    )
