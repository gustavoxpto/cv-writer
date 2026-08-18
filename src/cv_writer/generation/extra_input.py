"""Criterion 17: per application, the user may supply extra input (a cover-note angle, an
achievement not yet in the profile, emphasis instructions). Extra input is recorded with that
application, and the user is prompted to promote reusable additions into data/profile.yaml.

Pure function, no I/O — the actual YAML edit stays a human/UI action (spec open question 3:
data/profile.yaml is the only write path for the profile). This module only decides *what to
suggest*, never writes anything itself.
"""

from __future__ import annotations

from pydantic import BaseModel, Field

from .models import ExtraInput, ExtraInputKind


class PromotionSuggestion(BaseModel):
    """One piece of extra input worth prompting the user to add to data/profile.yaml."""

    extra_input_id: str = Field(min_length=1)
    text: str = Field(min_length=1)
    reason: str = Field(min_length=1)


def suggest_profile_promotions(extra_inputs: list[ExtraInput]) -> list[PromotionSuggestion]:
    """Only an ACHIEVEMENT explicitly marked `promote_candidate` is suggested — a cover-note
    angle or emphasis instruction is inherently one-off, in-the-moment framing for *this*
    application, not reusable evidence, so it's never a promotion candidate regardless of the
    flag.
    """
    return [
        PromotionSuggestion(
            extra_input_id=extra_input.id,
            text=extra_input.text,
            reason="marked as a reusable achievement — consider adding it to a job history",
        )
        for extra_input in extra_inputs
        if extra_input.kind == ExtraInputKind.ACHIEVEMENT and extra_input.promote_candidate
    ]
