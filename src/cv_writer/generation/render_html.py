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
#
# The second group are the metric-compatible libre twins: on a machine with no Arial (any
# stock Linux, including CI's ubuntu-latest runner), Chromium renders Liberation Sans, which
# is glyph-width-identical to Arial by design. Criterion 26's actual requirements — widely
# available, screen-and-print legible, non-decorative, embedded, no webfont that can fail to
# load — are met identically by either name, and the page lays out the same because the
# metrics match. They are named here, and in cv.html.jinja's font stack, so that this is a
# recorded decision rather than a silent OS fallback nobody chose. See ADR 0005.
_ARIAL_METRIC_TWINS = {"liberationsans", "liberation sans"}
_TIMES_METRIC_TWINS = {"liberationserif", "liberation serif"}
_CALIBRI_METRIC_TWINS = {"carlito"}

FONT_SHORTLIST = {
    "arial",
    "helvetica",
    "georgia",
    "calibri",
    "verdana",
    "times new roman",
} | _ARIAL_METRIC_TWINS | _TIMES_METRIC_TWINS | _CALIBRI_METRIC_TWINS

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
