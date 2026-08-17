"""Build a deterministic match report from a profile and a posting's requirement set
(criteria 13-16).

Pure function, no I/O, no LLM (criterion 14): the same profile + requirement set always
produce an identical MatchReport (a `reference_date` parameter, not the wall clock, drives
seniority's years-of-experience math, so tests can pin it). The score formula lives in
`SCORE_FORMULA` and rides along on every report (criterion 13: "the formula documented in the
report"), so a human can see exactly how the number was reached without reading source.
"""

from __future__ import annotations

from datetime import date

from cv_writer.ingestion.models import Requirement, RequirementKind, RequirementSet
from cv_writer.ingestion.requirements import word_boundary_pattern
from cv_writer.profile.models import Profile

from .models import MatchReport, MatchStatus, RequirementMatch
from .ranking import rank_evidence_bullets

# Required skills and things directly tied to "can you do the job" (seniority, language) count
# for more of the score than nice-to-haves; location/work-model is informational (see
# _match_location_work_model) so it carries the lowest weight.
_WEIGHTS: dict[RequirementKind, float] = {
    RequirementKind.REQUIRED_SKILL: 3.0,
    RequirementKind.SENIORITY: 2.0,
    RequirementKind.LANGUAGE: 2.0,
    RequirementKind.PREFERRED_SKILL: 1.0,
    RequirementKind.LOCATION_WORK_MODEL: 1.0,
}
_STATUS_VALUE: dict[MatchStatus, float] = {
    MatchStatus.MATCHED: 1.0,
    MatchStatus.PARTIAL: 0.5,
    MatchStatus.MISSING: 0.0,
}

SCORE_FORMULA = (
    "score = 100 * sum(weight(kind) * status_value(status) for each requirement) / "
    "sum(weight(kind)) — weights: required_skill=3, seniority=2, language=2, "
    "preferred_skill=1, location_work_model=1; status_value: matched=1.0, partial=0.5, "
    "missing=0.0"
)

# Rough years-of-experience floor for each seniority signal, used only to place the profile's
# total span on a matched/partial/missing scale — not a claim about what "senior" really means.
_SENIORITY_MIN_YEARS: dict[str, float] = {
    "intern": 0.0,
    "junior": 0.0,
    "mid": 2.0,
    "senior": 5.0,
    "lead": 6.0,
    "staff": 7.0,
    "principal": 8.0,
    "manager": 5.0,
    "director": 8.0,
}

# Proficiency labels treated as "working proficiency" for language matching. Mirrors the idea
# criterion 20 will later gate CV generation on, but this list is only an approximate signal
# for the match report — criterion 20 owns the authoritative check in slice 4.
_WORKING_PROFICIENCY_LEVELS = {
    "native",
    "fluent",
    "working",
    "professional",
    "advanced",
    "c1",
    "c2",
    "full professional",
}

# Requirement values that name a specific regional variant, and the markers a profile language
# name must contain to count as evidence for that variant specifically. A generic "Portuguese"
# entry does NOT satisfy either — the spec is explicit that PT-PT and PT-BR are distinct
# targets (criterion 21), and a fuzzy substring match ("portuguese" in "european portuguese")
# would otherwise claim a variant the profile never actually confirmed.
_VARIANT_LANGUAGE_MARKERS: dict[str, tuple[str, ...]] = {
    "european portuguese": ("european portuguese", "portuguese (european)", "pt-pt"),
    "brazilian portuguese": ("brazilian portuguese", "portuguese (brazilian)", "pt-br"),
}


def build_match_report(
    profile: Profile,
    requirement_set: RequirementSet,
    *,
    reference_date: date | None = None,
) -> MatchReport:
    today = reference_date or date.today()
    matches = [_match_requirement(profile, req, today) for req in requirement_set.requirements]
    return MatchReport(matches=matches, score=_score(matches), score_formula=SCORE_FORMULA)


def _score(matches: list[RequirementMatch]) -> float:
    total_weight = sum(_WEIGHTS[m.requirement.kind] for m in matches)
    if total_weight == 0:
        return 0.0
    earned = sum(_WEIGHTS[m.requirement.kind] * _STATUS_VALUE[m.status] for m in matches)
    return round(100 * earned / total_weight, 1)


def _match_requirement(
    profile: Profile, requirement: Requirement, today: date
) -> RequirementMatch:
    if requirement.kind in (RequirementKind.REQUIRED_SKILL, RequirementKind.PREFERRED_SKILL):
        return _match_skill(profile, requirement)
    if requirement.kind is RequirementKind.SENIORITY:
        return _match_seniority(profile, requirement, today)
    if requirement.kind is RequirementKind.LANGUAGE:
        return _match_language(profile, requirement)
    return _match_location_work_model(requirement)


def _skill_name_matches(value: str, skill_name: str) -> bool:
    """True if `value` (a canonical, single-word-ish requirement value like "sql") appears in
    `skill_name` as a whole word, or vice versa — word-boundary matching, not a plain substring
    test, so "sql" doesn't fuzzy-match "PostgreSQL"/"MySQL" and "git" doesn't fuzzy-match
    "GitHub Actions" (both true plain-substring false positives)."""
    return (
        word_boundary_pattern(value).search(skill_name) is not None
        or word_boundary_pattern(skill_name).search(value) is not None
    )


def _match_skill(profile: Profile, requirement: Requirement) -> RequirementMatch:
    value = requirement.value.lower()
    exact = next((s for s in profile.skills if s.name.lower() == value), None)
    fuzzy = exact or next(
        (s for s in profile.skills if _skill_name_matches(value, s.name.lower())), None
    )

    if exact is not None and exact.evidence:
        bullets = rank_evidence_bullets(profile, requirement.value, exact.evidence)
        return RequirementMatch(
            requirement=requirement,
            status=MatchStatus.MATCHED,
            evidence_skill=exact.name,
            evidence_bullets=bullets,
        )
    if exact is not None:
        return RequirementMatch(
            requirement=requirement,
            status=MatchStatus.PARTIAL,
            evidence_skill=exact.name,
            note=f"skill '{exact.name}' is claimed but has no evidencing job history",
        )
    if fuzzy is not None:
        bullets = rank_evidence_bullets(profile, requirement.value, fuzzy.evidence)
        return RequirementMatch(
            requirement=requirement,
            status=MatchStatus.PARTIAL,
            evidence_skill=fuzzy.name,
            evidence_bullets=bullets,
            note=f"closest profile skill is '{fuzzy.name}', not an exact match",
        )
    return RequirementMatch(
        requirement=requirement,
        status=MatchStatus.MISSING,
        note=f"no profile skill matches '{requirement.value}'",
    )


def _profile_experience_years(profile: Profile, today: date) -> float:
    """Total time actually covered by job histories, in years.

    Sums each history's own duration after merging overlapping/concurrent ones, rather than
    taking the span from the earliest start to the latest end — the span of two jobs eight
    years apart with nothing in between would otherwise count the gap between them as
    experience, which is exactly the kind of inflated, unevidenced claim the rest of this
    codebase's anti-fabrication posture is built to avoid.
    """
    if not profile.job_histories:
        return 0.0

    intervals = sorted(
        (h.start_date, today if h.end_date == "present" else h.end_date)
        for h in profile.job_histories
    )
    merged: list[list[date]] = []
    for start, end in intervals:
        if end < start:
            continue  # defensive; Profile's own validation should prevent this
        if merged and start <= merged[-1][1]:
            merged[-1][1] = max(merged[-1][1], end)
        else:
            merged.append([start, end])

    total_days = sum((end - start).days for start, end in merged)
    return round(total_days / 365.25, 1)


def _match_seniority(profile: Profile, requirement: Requirement, today: date) -> RequirementMatch:
    required_years = _SENIORITY_MIN_YEARS.get(requirement.value, 0.0)
    profile_years = _profile_experience_years(profile, today)
    note = (
        f"profile spans ~{profile_years} years of experience across job histories; "
        f"'{requirement.value}' expects ~{required_years}+ years"
    )
    if profile_years >= required_years:
        status = MatchStatus.MATCHED
    elif profile_years >= required_years - 2:
        status = MatchStatus.PARTIAL
    else:
        status = MatchStatus.MISSING
    return RequirementMatch(requirement=requirement, status=status, note=note)


def _match_language(profile: Profile, requirement: Requirement) -> RequirementMatch:
    value = requirement.value.lower()
    variant_markers = _VARIANT_LANGUAGE_MARKERS.get(value)

    if variant_markers is not None:
        found = next(
            (
                lang
                for lang in profile.languages
                if any(marker in lang.name.lower() for marker in variant_markers)
            ),
            None,
        )
        if found is None:
            return RequirementMatch(
                requirement=requirement,
                status=MatchStatus.MISSING,
                note=(
                    f"profile lists no language explicitly marked as '{requirement.value}' — "
                    "a generic 'Portuguese' entry isn't treated as evidence for a specific "
                    "regional variant (spec criterion 21 treats PT-PT and PT-BR as distinct)"
                ),
            )
    else:
        found = next(
            (
                lang
                for lang in profile.languages
                if value in lang.name.lower() or lang.name.lower() in value
            ),
            None,
        )
        if found is None:
            return RequirementMatch(
                requirement=requirement,
                status=MatchStatus.MISSING,
                note=f"profile lists no language matching '{requirement.value}'",
            )
    status = (
        MatchStatus.MATCHED
        if found.proficiency.lower() in _WORKING_PROFICIENCY_LEVELS
        else MatchStatus.PARTIAL
    )
    return RequirementMatch(
        requirement=requirement,
        status=status,
        note=f"profile lists {found.name} at '{found.proficiency}' proficiency",
    )


def _match_location_work_model(requirement: Requirement) -> RequirementMatch:
    # Profile has no structured work-model/relocation-preference field yet (identity.location
    # is just the human's current city, not a stated preference). Rather than guess a
    # matched/missing verdict from nothing, this is reported as PARTIAL with an explicit note —
    # "can't be automatically confirmed" is a more honest status than a fabricated MATCHED or
    # MISSING. Revisit if Profile grows a preferences field.
    return RequirementMatch(
        requirement=requirement,
        status=MatchStatus.PARTIAL,
        note=(
            f"'{requirement.value}' is a location/work-model requirement — the profile has no "
            "structured preference field to check it against automatically; review manually"
        ),
    )
