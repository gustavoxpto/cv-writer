"""Domain models for the match report (criteria 13-16)."""

from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, Field

from cv_writer.ingestion.models import Requirement


class MatchStatus(str, Enum):
    MATCHED = "matched"
    PARTIAL = "partial"
    MISSING = "missing"


class EvidenceBullet(BaseModel):
    """One profile bullet ranked as evidence for a requirement (criterion 16).

    Identified by `(history_id, bullet_index)` — a *ranking candidate*, not a citation.
    `Bullet` gained a real, stable `id` field in slice 4 (ADR 0004 decision 1), but this
    model is deliberately left as-is rather than switched over to it: `bullet_index` is what
    `rank_evidence_bullets()`/`select_bullets_within_budget()` (ranking.py) actually need to
    index back into `JobHistory.bullets`, and slice 4's `generation/source_ids.py` is the one
    place that turns one of these into a citable id (`bullet_source_id()`), keeping that
    concept at the boundary where it's actually needed rather than here.
    """

    history_id: str
    bullet_index: int = Field(ge=0)
    rank_score: float


class RequirementMatch(BaseModel):
    """One requirement's match status, evidence, and the reasoning behind it (criterion 13)."""

    requirement: Requirement
    status: MatchStatus
    evidence_skill: str | None = None
    evidence_bullets: list[EvidenceBullet] = Field(default_factory=list)
    note: str | None = None


class MatchReport(BaseModel):
    """The full match report for one profile + posting (criteria 13-15)."""

    matches: list[RequirementMatch]
    score: float
    score_formula: str = Field(min_length=1)

    def gaps(self) -> list[RequirementMatch]:
        """Missing and partial requirements, explicitly listed (criterion 15)."""
        return [m for m in self.matches if m.status != MatchStatus.MATCHED]
