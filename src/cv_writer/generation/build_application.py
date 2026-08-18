"""Pure mapper from a successful generate_cv() result into db.track_record.Application — no
DB I/O here. generation/ stays entirely DB-agnostic (matching/ingestion don't touch the DB
either): the caller — an integration test today, slice 5's UI later — is the one that calls
the existing insert_application() with the Application this builds. See
db/track_record.py's own docstring, which flags this module as its first real caller.
"""

from __future__ import annotations

from datetime import date

from cv_writer.db import Application
from cv_writer.ingestion.models import Posting

from .models import GeneratedCv
from .output_paths import OutputPaths


def build_application(
    *,
    generated_cv: GeneratedCv,
    posting: Posting,
    company: str,
    country: str,
    area: str,
    role_title: str,
    output_paths: OutputPaths,
    application_date: date,
    match_score: float | None,
    page_count: int,
    skills_featured: list[str],
) -> Application:
    """`company`/`country`/`area`/`role_title` are the caller's responsibility to supply
    (from the posting and/or user confirmation) rather than derived here — `Posting`'s own
    company/role_title/country fields are optional (unknown for many fetched postings) and
    `area` isn't on `Posting` at all, so guessing here would risk inventing data this module
    has no business inventing. `page_count` is likewise always the caller's (the human's,
    per criterion 24) choice, never computed here.

    `profile_bullet_ids` carries `generated_cv.source_ids_used` verbatim — both real profile
    bullet ids and any per-application extra-input ids the CV cited, distinguishable by the
    `extra-N` naming convention (source_ids.py). Track-record queries that care about "real"
    profile evidence only can filter on that convention; this mapper doesn't need Profile to
    do so."""
    return Application(
        application_date=application_date,
        company=company,
        country=country,
        area=area,
        role_title=role_title,
        source=posting.source,
        ingestion_tier=posting.ingestion_tier,
        match_score=match_score,
        output_language=generated_cv.variant or generated_cv.language,
        page_count=page_count,
        markdown_path=str(output_paths.markdown_path),
        pdf_path=str(output_paths.pdf_path),
        text_path=str(output_paths.text_path),
        skills_featured=skills_featured,
        profile_bullet_ids=generated_cv.source_ids_used,
    )
