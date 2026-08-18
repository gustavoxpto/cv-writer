"""The one place that resolves a citable "source id" (criteria 17-19a) to either a profile
bullet or a per-application extra input, and the one place that turns a matching-layer
`EvidenceBullet` (a ranking candidate — history_id + bullet_index, see
matching/models.py's own docstring) into that citable id.

`matching/models.py`'s `EvidenceBullet` is left untouched by this slice (see ADR 0004
decision 1) — it identifies a ranking candidate, not a citation. This module is the boundary
where a candidate becomes a citation.
"""

from __future__ import annotations

from cv_writer.matching.models import EvidenceBullet
from cv_writer.profile.models import Bullet, Profile

from .models import ExtraInput


def bullet_source_id(profile: Profile, evidence: EvidenceBullet) -> str:
    """Resolve an EvidenceBullet (history_id + bullet_index) to its profile bullet's stable
    citation id. Raises ValueError naming what's wrong, rather than an opaque
    StopIteration/IndexError, on a stale or dangling reference — matching this codebase's
    general "fail with a clear message naming the offending thing" posture (see
    ProfileValidationError)."""
    history = next((h for h in profile.job_histories if h.id == evidence.history_id), None)
    if history is None or evidence.bullet_index >= len(history.bullets):
        raise ValueError(
            f"EvidenceBullet(history_id={evidence.history_id!r}, "
            f"bullet_index={evidence.bullet_index}) does not resolve against this profile"
        )
    return history.bullets[evidence.bullet_index].id


def resolve_source(
    source_id: str, profile: Profile, extra_inputs: list[ExtraInput]
) -> Bullet | ExtraInput | None:
    """What does this source id point at? Profile bullet ids and extra-input ids are meant to
    share one string namespace without colliding (Profile's own validator enforces bullet-id
    uniqueness across the whole profile; extra input ids are assigned `extra-N` by
    convention) — but `ExtraInput.id` is still caller-supplied, so an accidental collision is
    checked for explicitly and raised loudly rather than silently preferring one over the
    other, which could let a numeric claim from unverifiable free-text extra input resolve
    against an unrelated real bullet's Metric and bypass the validator's "extra input has no
    metric to check against" rule (ADR 0004 decision 7).
    """
    bullet_match = next(
        (bullet for history in profile.job_histories for bullet in history.bullets
         if bullet.id == source_id),
        None,
    )
    extra_match = next((e for e in extra_inputs if e.id == source_id), None)

    if bullet_match is not None and extra_match is not None:
        raise ValueError(
            f"source id {source_id!r} collides between a profile bullet and an extra "
            "input — ids must be unique across both"
        )
    return bullet_match if bullet_match is not None else extra_match


def all_valid_source_ids(profile: Profile, extra_inputs: list[ExtraInput]) -> set[str]:
    """Every id a generated bullet is allowed to cite — every profile bullet id, plus every
    extra input id for this application."""
    bullet_ids = {
        bullet.id for history in profile.job_histories for bullet in history.bullets
    }
    extra_ids = {extra_input.id for extra_input in extra_inputs}
    return bullet_ids | extra_ids
