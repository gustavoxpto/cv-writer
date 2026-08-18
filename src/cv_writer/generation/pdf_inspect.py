"""Criteria 24, 26: read a rendered PDF back — page count (used by page_fit.py's real
page-fit measurement, criterion 24), extracted text, and embedded-font info (criterion 26's
"selectable, extractable text matching the Markdown source" and font-shortlist/embedding
rules). Used identically by production code (page_fit.py) and by integration tests — one
library (`pypdf`, ADR 0004 decision 5), one behavior, no test/production drift.
"""

from __future__ import annotations

from pathlib import Path

from pydantic import BaseModel
from pypdf import PdfReader


class FontInfo(BaseModel):
    """One font referenced by the PDF — its PostScript base name (subset tag stripped) and
    whether an embedded font program was found on its descriptor."""

    base_font: str
    embedded: bool


def page_count(path: Path) -> int:
    return len(PdfReader(str(path)).pages)


def extract_text(path: Path) -> str:
    reader = PdfReader(str(path))
    return "\n".join(page.extract_text() or "" for page in reader.pages)


def embedded_fonts(path: Path) -> list[FontInfo]:
    """Every distinct font referenced across the PDF's pages, deduplicated by base font name."""
    reader = PdfReader(str(path))
    fonts: dict[str, FontInfo] = {}

    for page in reader.pages:
        resources = page.get("/Resources")
        if resources is None:
            continue
        font_dict = resources.get("/Font")
        if font_dict is None:
            continue

        for font_ref in font_dict.values():
            font_obj = font_ref.get_object()
            base_font = _strip_subset_tag(str(font_obj.get("/BaseFont", "")))
            fonts[base_font] = FontInfo(base_font=base_font, embedded=_is_embedded(font_obj))

    return list(fonts.values())


def _strip_subset_tag(base_font: str) -> str:
    # A subsetted embedded font's /BaseFont looks like "ABCDEF+Arial" — the six-letter tag
    # plus "+" is a PDF-spec convention, not part of the real font name.
    name = base_font.lstrip("/")
    if "+" in name and name.split("+", 1)[0].isalpha() and len(name.split("+", 1)[0]) == 6:
        return name.split("+", 1)[1]
    return name


def _is_embedded(font_obj) -> bool:
    # Chromium's PDF export writes text as composite (Type0/CIDFontType2) fonts with
    # Identity-H encoding, not simple fonts — the /FontDescriptor carrying the embedded font
    # program lives on the *descendant* font, not on this top-level Type0 dict. Simple fonts
    # (Type1/TrueType) carry it directly, so both shapes are checked.
    descriptor = font_obj.get("/FontDescriptor")
    if descriptor is None and font_obj.get("/Subtype") == "/Type0":
        descendants = font_obj.get("/DescendantFonts")
        if descendants:
            descriptor = descendants[0].get_object().get("/FontDescriptor")
    if descriptor is None:
        return False
    descriptor_obj = descriptor.get_object()
    return any(key in descriptor_obj for key in ("/FontFile", "/FontFile2", "/FontFile3"))
