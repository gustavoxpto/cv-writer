"""Criterion 24, real Chromium-backed: fit_to_page_budget() measured against the actual
rendered PDF template, not a fake render_and_count callable (see
tests/unit/generation/test_page_fit.py for the pure-algorithm tests)."""

from cv_writer.generation.page_fit import fit_to_page_budget
from cv_writer.generation.pdf_inspect import page_count as pdf_page_count
from cv_writer.generation.render_html import render_html
from cv_writer.generation.render_pdf import render_pdf

# Long enough that ~20 of them reliably overflow one A4 page at 11pt body text, but a
# handful comfortably fit — real content, not a trivial one-liner, so the render is realistic.
_LONG_BULLET = (
    "Led a cross-functional initiative to redesign the checkout and payments pipeline, "
    "coordinating with backend, frontend, and data teams to cut end-to-end latency while "
    "keeping the rollout fully backward compatible for existing integrations."
)


def _render_bullets_and_count_pages(source_ids: list[str], tmp_path) -> int:
    markdown = "# Ana Example\n\n## Experience\n" + "\n".join(
        f"- {_LONG_BULLET} ({source_id})" for source_id in source_ids
    )
    html = render_html(markdown)
    pdf_path = render_pdf(html, tmp_path / f"cv-{len(source_ids)}.pdf")
    return pdf_page_count(pdf_path)


def test_fitting_a_short_bullet_list_needs_no_trimming(tmp_path):
    source_ids = [f"b{i}" for i in range(1, 4)]

    result = fit_to_page_budget(
        source_ids, lambda ids: _render_bullets_and_count_pages(ids, tmp_path)
    )

    assert result.achieved_one_page is True
    assert result.dropped_source_ids == []


def test_fitting_a_long_bullet_list_trims_until_it_fits_one_page(tmp_path):
    source_ids = [f"b{i}" for i in range(1, 21)]

    result = fit_to_page_budget(
        source_ids, lambda ids: _render_bullets_and_count_pages(ids, tmp_path)
    )

    assert result.achieved_one_page is True
    assert len(result.dropped_source_ids) > 0
    # Lowest-priority (last-listed) bullets are the ones dropped, highest-priority kept.
    assert result.fitted_source_ids[0] == "b1"
    assert "b20" in result.dropped_source_ids
