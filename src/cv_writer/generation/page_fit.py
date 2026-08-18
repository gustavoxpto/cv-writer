"""Criterion 24: one page is the target; two pages are the exception, and the human decides.
The tool aims to fit one page, and when the posting's requirements genuinely exceed that it
proposes two pages, showing exactly what a one-page version would drop. Page count is never
silently changed to make content fit.

This is the real, PDF-measured page-fit algorithm — replacing matching/ranking.py's
`select_bullets_within_budget()` char-budget heuristic as the *authoritative* mechanism (that
heuristic's own docstring already flags it as "a first cut... not the final page-fit
algorithm — that's slice 4, measured against the real PDF template"). It stays useful as a
cheap pre-filter (bounding how many candidates ever reach this slower, render-measured step),
but no longer decides the final page count on its own.

`render_and_count` is injected so this stays pure and fast to test — see
tests/unit/generation/test_page_fit.py for the algorithm itself, and
tests/integration/generation/test_page_fit.py for the real Chromium-backed version.
"""

from __future__ import annotations

from collections.abc import Callable

from pydantic import BaseModel


class PageFitResult(BaseModel):
    """What fit, what got dropped to make it fit (or didn't), and the honest final page
    count criterion 24 requires never be silently changed."""

    fitted_source_ids: list[str]
    dropped_source_ids: list[str]
    page_count: int
    achieved_one_page: bool


def fit_to_page_budget(
    ordered_source_ids: list[str],
    render_and_count: Callable[[list[str]], int],
    *,
    min_bullets: int = 1,
) -> PageFitResult:
    """`ordered_source_ids` must already be priority-sorted, most important first (matching/
    ranking.py's own ordering) — trimming always removes from the *tail* (lowest priority)
    first. Renders and re-measures after each trim until either 1 page is reached or
    `min_bullets` is hit; in the latter case this honestly reports achieved_one_page=False
    with two pages' worth of content and every dropped id, rather than ever silently
    committing to two pages.
    """
    current = list(ordered_source_ids)
    dropped: list[str] = []

    page_count = render_and_count(current)
    while page_count > 1 and len(current) > min_bullets:
        dropped.append(current.pop())
        page_count = render_and_count(current)

    return PageFitResult(
        fitted_source_ids=current,
        dropped_source_ids=dropped,
        page_count=page_count,
        achieved_one_page=(page_count == 1),
    )
