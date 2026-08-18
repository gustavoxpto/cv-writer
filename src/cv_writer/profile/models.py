"""Domain models for the profile: the single source of truth for real experience.

See specs/features/001-cv-writer.md, section A (criteria 1-6). These are plain Pydantic
models — no I/O, no database, no LLM. Loading YAML into these (and back out again as
validation errors) is the whole job of loader.py; this module only defines the shape and
the invariants criteria 1-5 require.
"""

from __future__ import annotations

from collections import Counter
from datetime import date
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

MIN_BULLETS_PER_HISTORY = 3
MAX_BULLETS_PER_HISTORY = 5


class ProfileModel(BaseModel):
    """Shared base for every profile model: strips leading/trailing whitespace from string
    fields before validation runs, so a whitespace-only value (e.g. situation: " ") can't
    satisfy min_length=1 and load as "valid" content (spec criterion 1)."""

    model_config = ConfigDict(str_strip_whitespace=True)


class Metric(ProfileModel):
    """A quantified claim attached to the bullet whose `result` it belongs to.

    Deliberately loose typing on `value` (a string, not a float): criterion 4's examples
    span "+37%", "R$1.2M", and "from 9 days to 2 days" — formats that don't share a single
    numeric shape. Keeping it a verbatim string avoids inventing false precision by forcing
    a parse; `unit`/`baseline` are optional structure on top of that string, not a
    replacement for it.
    """

    value: str = Field(min_length=1)
    unit: str | None = None
    baseline: str | None = None


class Bullet(ProfileModel):
    """One achievement, stored as explicit STAR fields (criterion 3)."""

    situation: str = Field(min_length=1)
    task: str = Field(min_length=1)
    action: str = Field(min_length=1)
    result: str = Field(min_length=1)
    metric: Metric | None = None


class JobHistory(ProfileModel):
    """One job history entry (criterion 2), with 3-5 STAR bullets (criterion 3) and at
    least one quantified metric somewhere in those bullets (criterion 4)."""

    id: str = Field(min_length=1)
    company: str = Field(min_length=1)
    role_title: str = Field(min_length=1)
    country: str = Field(min_length=1)
    area: str = Field(min_length=1)
    start_date: date
    end_date: date | Literal["present"]
    bullets: list[Bullet] = Field(
        min_length=MIN_BULLETS_PER_HISTORY, max_length=MAX_BULLETS_PER_HISTORY
    )

    @model_validator(mode="after")
    def _require_at_least_one_metric(self) -> JobHistory:
        if not any(bullet.metric is not None for bullet in self.bullets):
            raise ValueError(
                f"job history '{self.id}' ({self.company}) has no quantified metric on any "
                "bullet — every job history needs at least one (spec criterion 4)"
            )
        return self

    @model_validator(mode="after")
    def _require_start_before_end(self) -> JobHistory:
        if self.end_date != "present" and self.end_date < self.start_date:
            raise ValueError(
                f"job history '{self.id}' ({self.company}) has end_date {self.end_date} "
                f"before start_date {self.start_date}"
            )
        return self


class Skill(ProfileModel):
    """A skill claim, linked to the job histories that evidence it (criterion 5).

    `evidence` may be empty at load time — an unevidenced skill is valid, just flagged by
    `profile_check` (see check.py), not rejected here.
    """

    name: str = Field(min_length=1)
    category: str = Field(min_length=1)
    level: str | None = None
    years: float | None = None
    evidence: list[str] = Field(default_factory=list)


class Language(ProfileModel):
    name: str = Field(min_length=1)
    proficiency: str = Field(min_length=1)


class Education(ProfileModel):
    institution: str = Field(min_length=1)
    degree: str = Field(min_length=1)
    field: str | None = None
    start_date: date | None = None
    end_date: date | Literal["present"] | None = None


class Identity(ProfileModel):
    name: str = Field(min_length=1)
    email: str = Field(min_length=1)
    phone: str | None = None
    location: str | None = None
    links: dict[str, str] = Field(default_factory=dict)


class Profile(ProfileModel):
    """The whole profile: identity, skills, languages, education, job histories.

    Cross-field invariants that don't belong on a single nested model live here:
    job history ids must be unique, and every skill's evidence must point at a job
    history id that actually exists (a dangling reference is a data-integrity bug,
    not the "unevidenced" case criterion 5 treats as valid-but-worth-flagging).
    """

    identity: Identity
    languages: list[Language] = Field(default_factory=list)
    education: list[Education] = Field(default_factory=list)
    job_histories: list[JobHistory] = Field(default_factory=list)
    skills: list[Skill] = Field(default_factory=list)

    @model_validator(mode="after")
    def _cross_reference_evidence(self) -> Profile:
        history_ids = {history.id for history in self.job_histories}

        id_counts = Counter(history.id for history in self.job_histories)
        duplicate_ids = {history_id for history_id, count in id_counts.items() if count > 1}
        if duplicate_ids:
            raise ValueError(f"job_histories has duplicate id(s): {sorted(duplicate_ids)}")

        for skill in self.skills:
            unknown = [eid for eid in skill.evidence if eid not in history_ids]
            if unknown:
                raise ValueError(
                    f"skill '{skill.name}' has evidence referencing unknown job history "
                    f"id(s): {unknown} — evidence must reference an id in job_histories"
                )
        return self
