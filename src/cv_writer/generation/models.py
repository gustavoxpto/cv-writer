"""Domain models for generation: per-application extra input, the LLM's structured output
shape, the generated CV, and the anti-fabrication validator's failure shape.

See specs/features/001-cv-writer.md, sections D-E (criteria 17-28). Mirrors
ingestion/models.py's "result vs failure" pattern (Posting/IngestionFailure) with
GeneratedCv/GenerationFailure. Plain Pydantic models, no I/O.
"""

from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, Field, field_validator

from .pt_pt_checker import PtPtViolation


class ExtraInputKind(str, Enum):
    """The three kinds of per-application extra input criterion 17 names."""

    COVER_NOTE_ANGLE = "cover_note_angle"
    ACHIEVEMENT = "achievement"
    EMPHASIS = "emphasis"


class ExtraInput(BaseModel):
    """One piece of per-application extra input (criterion 17) — a cover-note angle, an
    achievement not yet in the profile, or emphasis instructions. Has its own stable id
    (assigned `extra-1`, `extra-2`, ... in submission order by the caller when not supplied)
    so generated bullets can cite it exactly like a profile bullet — see source_ids.py.
    """

    id: str = Field(min_length=1)
    kind: ExtraInputKind
    text: str = Field(min_length=1)
    promote_candidate: bool = False

    @field_validator("id")
    @classmethod
    def _id_not_purely_numeric(cls, value: str) -> str:
        # Same guard, same reason, as profile.models.Bullet._id_not_purely_numeric — both
        # id types flow into the same db.application_bullet_sources.profile_bullet_id
        # column (declared INTEGER; see ADR 0004 decision 1), which would silently coerce a
        # pure-digit id to SQLite's INTEGER storage class.
        if value.isdigit():
            raise ValueError(
                f"extra input id {value!r} is purely numeric — ids must contain at least "
                "one non-digit character"
            )
        return value


class GeneratedBulletDraft(BaseModel):
    """One bullet as the Rephraser hands it back — the LLM's structured-output shape
    (criterion 18: bounded to rephrasing/ordering, every bullet cites a source id). The
    validator (validator.py) independently re-checks this citation; it is never trusted on
    the LLM's say-so alone.

    `source_id` deliberately has no `min_length` constraint: criterion 19a requires the
    *validator* to reject "a bullet with no source id," which only makes sense to test if an
    empty source_id is a value this model can hold in the first place, rather than something
    Pydantic silently forbids upstream of the validator ever running.
    """

    text: str = Field(min_length=1)
    source_id: str = ""


class RephraseOutput(BaseModel):
    """The Rephraser's full structured output for one generation request."""

    bullets: list[GeneratedBulletDraft]


class GeneratedCv(BaseModel):
    """An accepted, validated, PT-PT-clean CV, ready to render (criteria 17-23 all passed).

    `markdown` is the validated bullet content itself (what the PT-PT checker scanned);
    `accepted_bullets` carries the same content structured, so the render pipeline
    (render_text.py) can build the full document (header/education/skills sections + these
    bullets) without re-parsing markdown back into data.
    """

    markdown: str = Field(min_length=1)
    language: str = Field(min_length=1)
    variant: str | None = None
    source_ids_used: list[str] = Field(default_factory=list)
    accepted_bullets: list[GeneratedBulletDraft] = Field(default_factory=list)


class ValidationFailure(BaseModel):
    """Why a generated CV was rejected (criterion 19), always naming the offending line."""

    reason: str = Field(min_length=1)
    offending_line: str
    line_number: int | None = None


class GenerationFailure(BaseModel):
    """Why generate_cv() refused to produce a CV — mirrors ingestion/models.py's
    Posting/IngestionFailure "result vs failure" pattern. Never a silent failure: `reason`
    always explains what happened, with the specific validation/PT-PT failures attached when
    that's what caused it."""

    reason: str = Field(min_length=1)
    validation_failures: list[ValidationFailure] = Field(default_factory=list)
    pt_pt_violations: list[PtPtViolation] = Field(default_factory=list)
