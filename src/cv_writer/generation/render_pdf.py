"""Criteria 25-26: render an HTML CV document to PDF through headless Chromium — the same
browser ingestion tier 2 already uses (ADR 0004 decision 2: no WeasyPrint spike, Chromium is
already a proven dependency in this environment). Mirrors fetch_tier2.py's own
`sync_playwright()` usage style for consistency across the codebase.

`print_background=True` is deliberate: without it Chromium omits background colors/fills when
printing, and criterion 26 requires the page to actually render white (not transparent) so it
survives being printed or photocopied.
"""

from __future__ import annotations

from pathlib import Path

from playwright.sync_api import sync_playwright

DEFAULT_PAGE_FORMAT = "A4"


def render_pdf(html: str, output_path: Path, *, page_format: str = DEFAULT_PAGE_FORMAT) -> Path:
    """Render `html` to a PDF at `output_path`, creating parent directories as needed."""
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        try:
            page = browser.new_page()
            page.set_content(html, wait_until="load")
            page.pdf(path=str(output_path), format=page_format, print_background=True)
        finally:
            browser.close()

    return output_path
