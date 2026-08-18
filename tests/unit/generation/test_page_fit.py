"""Criterion 24: one page is the target, two pages the exception, and the human decides;
the tool shows exactly what a one-page version would drop; page count is never silently
changed. `fit_to_page_budget()` is the real, PDF-measured page-fit algorithm (replacing
matching/ranking.py's char-budget first cut, see that module's own docstring) — pure and
testable here via an injected `render_and_count` callable; the real Chromium-backed version
is exercised in tests/integration/generation/test_page_fit.py.
"""

from cv_writer.generation.page_fit import fit_to_page_budget


def _counter_that_fits_at(max_bullets: int):
    """A fake render_and_count: reports 1 page once the candidate list is short enough."""

    def render_and_count(source_ids: list[str]) -> int:
        return 1 if len(source_ids) <= max_bullets else 2

    return render_and_count


def test_already_one_page_drops_nothing():
    result = fit_to_page_budget(["b1", "b2", "b3"], _counter_that_fits_at(5))

    assert result.fitted_source_ids == ["b1", "b2", "b3"]
    assert result.dropped_source_ids == []
    assert result.achieved_one_page is True
    assert result.page_count == 1


def test_trims_from_the_tail_lowest_priority_first_until_it_fits():
    result = fit_to_page_budget(["b1", "b2", "b3", "b4", "b5"], _counter_that_fits_at(2))

    assert result.fitted_source_ids == ["b1", "b2"]
    assert result.dropped_source_ids == ["b5", "b4", "b3"]
    assert result.achieved_one_page is True


def test_stops_at_the_minimum_bullet_floor_and_reports_two_pages_honestly():
    always_two_pages = lambda source_ids: 2  # noqa: E731 — trivial local test fake
    result = fit_to_page_budget(["b1", "b2", "b3"], always_two_pages, min_bullets=1)

    assert result.achieved_one_page is False
    assert result.page_count == 2
    assert len(result.fitted_source_ids) == 1
    assert result.dropped_source_ids == ["b3", "b2"]


def test_never_trims_below_min_bullets_even_if_it_never_fits():
    always_two_pages = lambda source_ids: 2  # noqa: E731
    result = fit_to_page_budget(["b1", "b2"], always_two_pages, min_bullets=2)

    assert result.fitted_source_ids == ["b1", "b2"]
    assert result.dropped_source_ids == []
