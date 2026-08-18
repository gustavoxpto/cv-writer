"""Criteria 25, 27, 28 (ADR 0005 decision 6): write the three generated CV artifacts —
Markdown, plain text, and PDF — to disk, at the collision-free paths output_paths.py already
computed.

Nothing in generation/ wrote a `.md`/`.txt` file before this slice: render_text.py/
render_html.py/render_pdf.py all only ever produced in-memory content, and slice 4 left "write
these to disk" to whichever caller needed it next. That caller is this module, not the web
layer (slice 5) — putting real output logic in web/ would bury criteria 25-28 behind a web
framework where only an e2e test could reach them, against the spirit of criterion 34 even
though it wouldn't violate its letter (write_output.py itself has no web-framework import).
`render_pdf_fn` is injectable so tests/unit/generation/test_write_output.py runs without
Chromium; tests/integration/generation/test_write_output.py exercises the real one.
"""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

from pydantic import BaseModel

from cv_writer.profile.models import Profile

from .models import GeneratedCv
from .output_paths import OutputPaths
from .render_html import render_html
from .render_pdf import render_pdf as _default_render_pdf
from .render_text import render_markdown, render_plain_text


class WrittenArtifacts(BaseModel):
    """Where the three generated files actually landed (criteria 25, 27, 28) — the same three
    paths as OutputPaths, returned separately so a caller can tell "here's where I planned to
    write" (OutputPaths) apart from "here's confirmation it's actually on disk now"
    (WrittenArtifacts)."""

    model_config = {"arbitrary_types_allowed": True}

    markdown_path: Path
    pdf_path: Path
    text_path: Path


def write_artifacts(
    *,
    cv: GeneratedCv,
    profile: Profile,
    paths: OutputPaths,
    render_pdf_fn: Callable[[str, Path], Path] = _default_render_pdf,
) -> WrittenArtifacts:
    """Render `cv` (Markdown -> plain text, and Markdown -> HTML -> PDF) and write all three to
    `paths`, creating the output directory if it doesn't exist yet. Never overwrites a
    *different* application's files — `paths` is expected to already be the collision-free
    result of build_output_paths() (criterion 28); this function only writes to exactly the
    three paths it's given.
    """
    paths.markdown_path.parent.mkdir(parents=True, exist_ok=True)

    markdown_text = render_markdown(cv, profile)
    plain_text = render_plain_text(cv, profile)
    html = render_html(markdown_text, language=cv.language, title=profile.identity.name)

    paths.markdown_path.write_text(markdown_text, encoding="utf-8")
    paths.text_path.write_text(plain_text, encoding="utf-8")
    render_pdf_fn(html, paths.pdf_path)

    return WrittenArtifacts(
        markdown_path=paths.markdown_path,
        pdf_path=paths.pdf_path,
        text_path=paths.text_path,
    )
