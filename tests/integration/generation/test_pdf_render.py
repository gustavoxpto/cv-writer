"""Criterion 26: the PDF template's actual test — the rendered PDF's extracted text matches
the Markdown source's content, and its font is on the documented shortlist and actually
embedded. Real Playwright + Chromium (same posture as ingestion tier 2's integration tests) —
renders to a temp dir, never a live/shared resource.
"""

from cv_writer.generation.pdf_inspect import embedded_fonts, extract_text, page_count
from cv_writer.generation.render_html import FONT_SHORTLIST, render_html
from cv_writer.generation.render_pdf import render_pdf


def test_pdf_extracted_text_matches_the_markdown_source(tmp_path):
    markdown_text = (
        "# Ana Example\n\nana@example.com\n\n## Experience\n"
        "- Cut checkout p99 latency by 77%, from 1.4s to 320ms.\n"
        "- Automated deploys, cutting deploy time from 45min to ~2min.\n"
    )
    html = render_html(markdown_text, title="Ana Example CV")
    pdf_path = render_pdf(html, tmp_path / "cv.pdf")

    extracted = extract_text(pdf_path)

    assert "Ana Example" in extracted
    assert "Cut checkout p99 latency by 77%" in extracted
    assert "Automated deploys" in extracted


def test_pdf_font_is_on_the_documented_shortlist_and_embedded(tmp_path):
    html = render_html("# Ana Example\n\n## Experience\n- One bullet with enough text.\n")
    pdf_path = render_pdf(html, tmp_path / "cv.pdf")

    fonts = embedded_fonts(pdf_path)

    assert len(fonts) > 0
    for font in fonts:
        assert font.base_font.lower() in FONT_SHORTLIST or any(
            shortlisted in font.base_font.lower() for shortlisted in FONT_SHORTLIST
        )
        assert font.embedded is True


def test_short_cv_fits_on_one_page(tmp_path):
    html = render_html("# Ana Example\n\n## Experience\n- One short bullet.\n")
    pdf_path = render_pdf(html, tmp_path / "cv.pdf")

    assert page_count(pdf_path) == 1
