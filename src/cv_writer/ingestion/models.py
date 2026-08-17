"""Domain models for ingestion: a fetched/pasted posting and its extracted requirements.

See specs/features/001-cv-writer.md, section B (criteria 7-12). Plain Pydantic models, no I/O —
fetching lives in fetch_tier1.py/fetch_tier2.py/fetch_tier3.py, orchestration in pipeline.py,
extraction in requirements.py.
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field

PASTED_SOURCE = "pasted"


class Posting(BaseModel):
    """A job posting, however it arrived (criteria 7-9).

    `source` is the URL for tier 1/2, or the literal "pasted" for tier 3 (criterion 8: pasted
    and fetched postings are otherwise indistinguishable downstream). `ingestion_tier` records
    which of the three tiers produced this posting (criterion 9). `company`/`role_title`/
    `country` are known immediately for a pasted posting (the user supplies them) and may be
    filled in later for a fetched one — left optional here rather than guessed from the page.
    """

    raw_text: str = Field(min_length=1)
    source: str = Field(min_length=1)
    fetched_at: datetime
    ingestion_tier: int = Field(ge=1, le=3)
    company: str | None = None
    role_title: str | None = None
    country: str | None = None


class IngestionFailure(BaseModel):
    """What happened when ingestion could not produce a Posting (criteria 9.3, 10, 11).

    Never a silent failure: `reason` is always human-readable and `tier_attempted` names the
    last tier that ran, so the caller (eventually the UI) can offer the paste fallback with an
    explanation rather than an empty result.
    """

    tier_attempted: int = Field(ge=1, le=2)
    reason: str = Field(min_length=1)


class RequirementKind(str, Enum):
    REQUIRED_SKILL = "required_skill"
    PREFERRED_SKILL = "preferred_skill"
    SENIORITY = "seniority"
    LANGUAGE = "language"
    LOCATION_WORK_MODEL = "location_work_model"


class Requirement(BaseModel):
    """One structured requirement extracted from posting text (criterion 12).

    `value` is the normalized form (e.g. "python", "senior", "german") used for matching;
    `source_phrase` is the verbatim substring of the posting text the extractor matched, kept
    so a human can always see *why* the tool believes this requirement is there.
    """

    kind: RequirementKind
    value: str = Field(min_length=1)
    source_phrase: str = Field(min_length=1)


class RequirementSet(BaseModel):
    requirements: list[Requirement] = Field(default_factory=list)

    def of_kind(self, kind: RequirementKind) -> list[Requirement]:
        return [r for r in self.requirements if r.kind == kind]
