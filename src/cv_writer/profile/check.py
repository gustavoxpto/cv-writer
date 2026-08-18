"""`profile check`: reports worth surfacing that don't fail validation.

Two things load_profile() accepts but a human should probably still fix (criteria 4 and 5):
  - a skill claimed with no evidencing history (loaded, just unevidenced),
  - a job history where only one of several bullets is quantified (more proof is better).

Kept as a pure function over an already-loaded Profile — no I/O, no CLI here — so it's
testable the same way as the models, and any future CLI/UI surface (out of scope for slice 1)
just calls this and renders the result.
"""

from __future__ import annotations

from pydantic import BaseModel

from .models import Profile


class CheckWarning(BaseModel):
    kind: str
    subject: str
    message: str


def profile_check(profile: Profile) -> list[CheckWarning]:
    warnings: list[CheckWarning] = []

    for skill in profile.skills:
        if not skill.evidence:
            warnings.append(
                CheckWarning(
                    kind="unevidenced_skill",
                    subject=skill.name,
                    message=(
                        f"skill '{skill.name}' has no evidencing job history — consider "
                        "linking it to one, or dropping the claim"
                    ),
                )
            )

    for history in profile.job_histories:
        quantified_count = sum(1 for bullet in history.bullets if bullet.metric is not None)
        # No need to also guard on len(history.bullets) > 1: the schema (MIN_BULLETS_PER_HISTORY
        # in models.py) already requires 3-5 bullets per history, so "exactly one quantified"
        # is meaningful on its own here.
        if quantified_count == 1:
            warnings.append(
                CheckWarning(
                    kind="single_quantified_bullet",
                    subject=history.id,
                    message=(
                        f"job history '{history.id}' ({history.company}) has only one "
                        f"quantified bullet out of {len(history.bullets)} — more proof is "
                        "better"
                    ),
                )
            )

    return warnings
