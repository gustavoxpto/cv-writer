"""Criteria 25-26: Markdown -> HTML through a single consistent visual template. See ADR
0004 decisions 3-4: Markdown's core renderer only (no `tables` extension — the enforcement
mechanism for criterion 26's "no tables" ATS rule) wrapped in one Jinja2 print template that
references a documented-shortlist font by name only (no bundled font file; the shortlisted
families are standard pre-installed system fonts, and headless Chromium embeds whatever font
actually rendered the page automatically when exporting to PDF — see render_pdf.py).
"""

from __future__ import annotations

from pathlib import Path

import markdown as markdown_lib
from jinja2 import Environment, FileSystemLoader, select_autoescape

TEMPLATES_DIR = Path(__file__).parent / "templates"

# The documented font shortlist criterion 26 requires — one of these, embedded, at >=10pt.
FONT_SHORTLIST = {"arial", "helvetica", "georgia", "calibri", "verdana", "times new roman"}

_env = Environment(
    loader=FileSystemLoader(TEMPLATES_DIR),
    autoescape=select_autoescape(enabled_extensions=("html", "jinja")),
)


def render_html(markdown_text: str, *, language: str = "en", title: str = "CV") -> str:
    """Render Markdown CV content into a full, self-contained HTML document ready to print to
    PDF (render_pdf.py) — the Markdown -> HTML step uses only the `markdown` package's core
    renderer (no `tables`/other extensions enabled), which is what keeps the ATS-safety rule
    (no tables, no text boxes) true by construction rather than by post-processing."""
    body_html = markdown_lib.markdown(markdown_text)  # core renderer only — see module docstring
    template = _env.get_template("cv.html.jinja")
    return template.render(body=body_html, language=language, title=title)
