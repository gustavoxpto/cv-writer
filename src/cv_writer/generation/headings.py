"""AC-004: the localized structural strings render_markdown() needs -- the experience,
education and skills section headings -- keyed by the resolved output language.

Design boundary B3: this module is pure data. It imports nothing from `cv_writer` and
touches no disk, so the render path (render_text.py -> headings.py) does not drag
`ingestion` or the pt_pt_terms.yaml load in behind it, and the dependency direction stays
trivially acyclic.

Design decision 4: `section_headings()` raises `ValueError` on a language it has no
translation for -- it never falls back to English. A silent English fallback is the exact
2026-08-19 bug this spec exists to fix (L-004: prefer a loud failure to a quiet wrong
result). Draft translations only (OQ-2, non-blocking, open) -- worth a native-speaker read,
not a linguistic authority yet.
"""

from __future__ import annotations

from pydantic import BaseModel


class SectionHeadings(BaseModel, frozen=True):
    """The three section headings render_markdown() emits, in one language."""

    experience: str
    education: str
    skills: str


# One entry per language cv_writer.generation.language.SUPPORTED_LANGUAGES knows -- this
# module deliberately does not import that dict (B3: no dependency on cv_writer at all), so
# test_headings.py checks the two key sets match instead.
SECTION_HEADINGS: dict[str, SectionHeadings] = {
    "english": SectionHeadings(
        experience="Experience",
        education="Education",
        skills="Skills",
    ),
    "portuguese": SectionHeadings(
        experience="Experiência Profissional",
        education="Formação",
        skills="Competências",
    ),
    "german": SectionHeadings(
        experience="Berufserfahrung",
        education="Ausbildung",
        skills="Kenntnisse",
    ),
    "spanish": SectionHeadings(
        experience="Experiencia",
        education="Educación",
        skills="Habilidades",
    ),
}


def section_headings(language: str) -> SectionHeadings:
    """Look up the section headings for `language`, normalized with `.strip().lower()` --
    `GeneratedCv.language` is a free `str` field (no Enum), so a capitalized or padded value
    must not raise. Raises `ValueError` for a language with no translation, naming both the
    offending value and the supported set (design decision 4 -- no silent English fallback).
    """
    normalized = language.strip().lower()
    try:
        return SECTION_HEADINGS[normalized]
    except KeyError:
        supported = ", ".join(sorted(SECTION_HEADINGS))
        raise ValueError(
            f"{normalized!r} has no section-heading translation "
            f"(supported: {supported})"
        ) from None
