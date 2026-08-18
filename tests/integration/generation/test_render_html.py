"""Criteria 25-26: Markdown renders into a full HTML document through the one consistent
visual template, with the ATS "no tables" rule enforced by construction (core Markdown
renderer only, ADR 0004 decision 3)."""

from cv_writer.generation.render_html import FONT_SHORTLIST, render_html


def test_render_html_produces_a_full_html_document_containing_the_bullet_text():
    html = render_html("## Experience\n- Cut checkout latency by 77%.\n", title="Ana Example CV")

    assert "<html" in html
    assert "Cut checkout latency by 77%." in html
    assert "Ana Example CV" in html


def test_render_html_never_produces_a_table_even_if_markdown_looks_table_like():
    # Core Markdown renderer only — no `tables` extension enabled (ADR 0004 decision 3), so
    # this pipe-delimited text is never turned into an ATS-unsafe <table>.
    markdown_text = "| Skill | Years |\n|---|---|\n| Python | 6 |\n"

    html = render_html(markdown_text)

    assert "<table" not in html.lower()


def test_render_html_references_a_shortlisted_font_by_name():
    html = render_html("- Some bullet\n")

    assert any(font in html.lower() for font in FONT_SHORTLIST)
