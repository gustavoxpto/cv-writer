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

    Identified by `(history_id, bullet_index)` rather than a bullet id — `Bullet` has no
    stable id of its own yet (flagged in the slice-2 pairing note as an open point for slice
    4, when generation needs to cite "the id of the profile bullet a CV line was derived
    from"). `bullet_index` is the bullet's position within `JobHistory.bullets`.
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
