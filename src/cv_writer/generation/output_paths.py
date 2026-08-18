"""Criterion 28: output paths are deterministic and collision-free per application (date +
company + role slug), and generating twice for the same application produces a new version
rather than overwriting a previous artifact.

Known, deliberate limitation (flagged by a code-review pass, not fixed): this only checks
existence, it doesn't reserve the chosen path — two concurrent generation runs for the same
application, started before either has written output, could compute the same version and
the second write would overwrite the first. Not fixed here because the spec scopes this tool
to a single, localhost, single-user session (see specs/features/001-cv-writer.md's "Out of
scope": "Multi-user, authentication, hosting... Localhost single-user only") — a locking/
reservation mechanism would be real effort spent on a scenario this tool's stated audience
doesn't hit. Revisit if that scoping ever changes.
"""

from __future__ import annotations

import re
from datetime import date
from pathlib import Path

from pydantic import BaseModel

DEFAULT_OUTPUT_DIR = Path("data") / "applications"

_SLUG_STRIP_PATTERN = re.compile(r"[^a-z0-9]+")


class OutputPaths(BaseModel):
    """The three artifact paths for one generated application (criteria 25-27)."""

    model_config = {"arbitrary_types_allowed": True}

    markdown_path: Path
    pdf_path: Path
    text_path: Path


def build_output_paths(
    application_date: date,
    company: str,
    role_title: str,
    *,
    output_dir: Path = DEFAULT_OUTPUT_DIR,
) -> OutputPaths:
    """Deterministic base name (date + company + role slug); if that base name already has
    files on disk (a prior generation), append -v2, -v3, ... until an unused one is found —
    generating twice never overwrites a previous artifact (criterion 28)."""
    base_slug = f"{application_date.isoformat()}-{_slugify(company)}-{_slugify(role_title)}"

    version = 1
    while True:
        slug = base_slug if version == 1 else f"{base_slug}-v{version}"
        markdown_path = output_dir / f"{slug}.md"
        pdf_path = output_dir / f"{slug}.pdf"
        text_path = output_dir / f"{slug}.txt"
        if not (markdown_path.exists() or pdf_path.exists() or text_path.exists()):
            return OutputPaths(markdown_path=markdown_path, pdf_path=pdf_path, text_path=text_path)
        version += 1


def _slugify(value: str) -> str:
    return _SLUG_STRIP_PATTERN.sub("-", value.strip().lower()).strip("-")
