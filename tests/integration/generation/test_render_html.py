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


def test_font_stack_names_a_metric_compatible_face_for_machines_without_arial():
    # Regression (found by CI the first run after slice 5 wired Chromium in): ubuntu-latest
    # has neither Arial nor Helvetica, so Chromium silently fell back to Liberation Sans and
    # the embedded-font assertion in test_pdf_render.py failed. Liberation Sans is
    # glyph-width-identical to Arial, so the fix is to name it rather than to let the OS
    # choose unrecorded — the stack must still prefer Arial where it exists.
    html = render_html("- Some bullet\n")

    # Assert against the declaration itself, not the whole document — both names also appear
    # in the CSS comment above it, which would make a document-wide ordering check meaningless.
    font_family = next(
        line.strip() for line in html.splitlines() if line.strip().startswith("font-family:")
    ).lower()
    assert "liberation sans" in font_family
    assert font_family.index("arial") < font_family.index("liberation sans")


def test_the_arial_metric_twin_is_on_the_documented_shortlist():
    # The other half of the same regression: naming the font in the stack is not enough if
    # criterion 26's shortlist still rejects what actually got embedded on Linux.
    assert "liberationsans" in FONT_SHORTLIST
