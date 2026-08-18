"""Criteria 13-16: build_match_report() is a deterministic, pure function producing a
per-requirement matched/partial/missing status, an overall score with a documented formula,
and ranked evidence bullets — no I/O, no LLM."""

from cv_writer.ingestion.models import Requirement, RequirementKind, RequirementSet
from cv_writer.matching.matcher import SCORE_FORMULA, build_match_report
from cv_writer.matching.models import MatchStatus


def _requirements(*items: tuple[RequirementKind, str]) -> RequirementSet:
    return RequirementSet(
        requirements=[
            Requirement(kind=kind, value=value, source_phrase=value) for kind, value in items
        ]
    )


def test_matched_status_for_an_evidenced_skill(profile, reference_date):
    reqs = _requirements((RequirementKind.REQUIRED_SKILL, "python"))

    report = build_match_report(profile, reqs, reference_date=reference_date)

    match = report.matches[0]
    assert match.status is MatchStatus.MATCHED
    assert match.evidence_skill == "Python"
    assert len(match.evidence_bullets) > 0


def test_partial_status_for_a_skill_claimed_without_evidence(profile, reference_date):
    reqs = _requirements((RequirementKind.REQUIRED_SKILL, "docker"))

    report = build_match_report(profile, reqs, reference_date=reference_date)

    match = report.matches[0]
    assert match.status is MatchStatus.PARTIAL
    assert "no evidencing job history" in match.note


def test_missing_status_for_a_skill_absent_from_the_profile(profile, reference_date):
    reqs = _requirements((RequirementKind.REQUIRED_SKILL, "rust"))

    report = build_match_report(profile, reqs, reference_date=reference_date)

    match = report.matches[0]
    assert match.status is MatchStatus.MISSING
    assert match.evidence_bullets == []


def test_language_matched_at_working_proficiency_partial_below_it(profile, reference_date):
    reqs = _requirements(
        (RequirementKind.LANGUAGE, "english"), (RequirementKind.LANGUAGE, "german")
    )

    report = build_match_report(profile, reqs, reference_date=reference_date)

    by_value = {m.requirement.value: m for m in report.matches}
    assert by_value["english"].status is MatchStatus.MATCHED
    assert by_value["german"].status is MatchStatus.PARTIAL


def test_language_missing_when_profile_has_no_matching_language(profile, reference_date):
    reqs = _requirements((RequirementKind.LANGUAGE, "french"))

    report = build_match_report(profile, reqs, reference_date=reference_date)

    assert report.matches[0].status is MatchStatus.MISSING


def test_seniority_matched_when_profile_years_meet_the_threshold(profile, reference_date):
    # profile spans job-acme's start (2020-01-15) to "present" (reference_date, 2026-08-17):
    # ~6.6 years, comfortably above "senior"'s ~5-year floor.
    reqs = _requirements((RequirementKind.SENIORITY, "senior"))

    report = build_match_report(profile, reqs, reference_date=reference_date)

    assert report.matches[0].status is MatchStatus.MATCHED


def test_seniority_partial_when_close_but_short_of_the_threshold(profile, reference_date):
    # "principal" expects ~8+ years; profile has ~6.6 — within the 2-year partial buffer.
    reqs = _requirements((RequirementKind.SENIORITY, "principal"))

    report = build_match_report(profile, reqs, reference_date=reference_date)

    assert report.matches[0].status is MatchStatus.PARTIAL


def test_location_work_model_is_reported_as_informational_partial(profile, reference_date):
    reqs = _requirements((RequirementKind.LOCATION_WORK_MODEL, "remote"))

    report = build_match_report(profile, reqs, reference_date=reference_date)

    match = report.matches[0]
    assert match.status is MatchStatus.PARTIAL
    assert "review manually" in match.note


def test_score_formula_travels_with_the_report(profile, reference_date):
    reqs = _requirements((RequirementKind.REQUIRED_SKILL, "python"))

    report = build_match_report(profile, reqs, reference_date=reference_date)

    assert report.score_formula == SCORE_FORMULA
    assert report.score == 100.0  # sole requirement, fully matched


def test_score_reflects_a_mix_of_matched_and_missing_requirements(profile, reference_date):
    reqs = _requirements(
        (RequirementKind.REQUIRED_SKILL, "python"),  # matched, weight 3
        (RequirementKind.REQUIRED_SKILL, "rust"),  # missing, weight 3
    )

    report = build_match_report(profile, reqs, reference_date=reference_date)

    assert report.score == 50.0


def test_gaps_lists_missing_and_partial_but_not_matched(profile, reference_date):
    reqs = _requirements(
        (RequirementKind.REQUIRED_SKILL, "python"),  # matched
        (RequirementKind.REQUIRED_SKILL, "docker"),  # partial
        (RequirementKind.REQUIRED_SKILL, "rust"),  # missing
    )

    report = build_match_report(profile, reqs, reference_date=reference_date)

    gap_values = {m.requirement.value for m in report.gaps()}
    assert gap_values == {"docker", "rust"}


def test_build_match_report_is_deterministic(profile, reference_date):
    reqs = _requirements(
        (RequirementKind.REQUIRED_SKILL, "python"),
        (RequirementKind.SENIORITY, "senior"),
        (RequirementKind.LANGUAGE, "english"),
    )

    first = build_match_report(profile, reqs, reference_date=reference_date)
    second = build_match_report(profile, reqs, reference_date=reference_date)

    assert first.model_dump() == second.model_dump()


def test_seniority_does_not_count_a_gap_between_jobs_as_experience():
    # Regression: two 1-year jobs eight years apart is 2 real years of experience, not the
    # ~10-year span between the earliest start and the latest end.
    from datetime import date
    from itertools import count

    from cv_writer.profile.models import Bullet, Identity, JobHistory, Metric, Profile

    ids = count(1)

    def bullet(text):
        return Bullet(
            id=f"b{next(ids)}",
            situation=text,
            task=text,
            action=text,
            result=text,
            metric=Metric(value="+1", unit="x"),
        )

    early_job = JobHistory(
        id="early",
        company="A",
        role_title="Engineer",
        country="Portugal",
        area="Eng",
        start_date=date(2010, 1, 1),
        end_date=date(2011, 1, 1),
        bullets=[bullet("did work"), bullet("did more work"), bullet("did even more work")],
    )
    late_job = JobHistory(
        id="late",
        company="B",
        role_title="Engineer",
        country="Portugal",
        area="Eng",
        start_date=date(2019, 1, 1),
        end_date=date(2020, 1, 1),
        bullets=[bullet("did work"), bullet("did more work"), bullet("did even more work")],
    )
    gapped_profile = Profile(
        identity=Identity(name="X", email="x@example.com"),
        job_histories=[early_job, late_job],
        skills=[],
    )

    reqs = _requirements((RequirementKind.SENIORITY, "senior"))  # expects ~5+ years

    report = build_match_report(gapped_profile, reqs, reference_date=date(2026, 1, 1))

    # ~2 real years worked, nowhere near "senior"'s ~5-year floor (even with the 2-year
    # partial buffer) — the old span-based calculation (~16 years) would have MATCHED this.
    assert report.matches[0].status is MatchStatus.MISSING


def test_fuzzy_skill_match_does_not_cross_match_unrelated_substrings(reference_date):
    # Regression: plain substring matching made "sql" fuzzy-match "PostgreSQL" and "git"
    # fuzzy-match "GitHub Actions" — word-boundary matching must reject both.
    from cv_writer.profile.models import Identity, Profile, Skill

    profile_with_similar_names = Profile(
        identity=Identity(name="X", email="x@example.com"),
        job_histories=[],
        skills=[
            Skill(name="PostgreSQL", category="database", evidence=[]),
            Skill(name="GitHub Actions", category="tool", evidence=[]),
        ],
    )
    reqs = _requirements(
        (RequirementKind.REQUIRED_SKILL, "sql"), (RequirementKind.REQUIRED_SKILL, "git")
    )

    report = build_match_report(
        profile_with_similar_names, reqs, reference_date=reference_date
    )

    by_value = {m.requirement.value: m for m in report.matches}
    assert by_value["sql"].status is MatchStatus.MISSING
    assert by_value["git"].status is MatchStatus.MISSING


def test_generic_portuguese_is_not_evidence_for_a_specific_regional_variant(reference_date):
    # Regression: "portuguese" is a substring of "european portuguese", so a naive fuzzy match
    # let a generic profile entry satisfy a PT-PT-specific requirement — contradicting the
    # spec's own PT-PT/PT-BR distinction (criterion 21).
    from cv_writer.profile.models import Identity, Language, Profile

    profile_with_generic_portuguese = Profile(
        identity=Identity(name="X", email="x@example.com"),
        languages=[Language(name="Portuguese", proficiency="native")],
        job_histories=[],
        skills=[],
    )
    reqs = _requirements((RequirementKind.LANGUAGE, "european portuguese"))

    report = build_match_report(
        profile_with_generic_portuguese, reqs, reference_date=reference_date
    )

    assert report.matches[0].status is MatchStatus.MISSING


def test_explicit_variant_marker_does_satisfy_the_variant_requirement(reference_date):
    from cv_writer.profile.models import Identity, Language, Profile

    profile_with_pt_pt = Profile(
        identity=Identity(name="X", email="x@example.com"),
        languages=[Language(name="Portuguese (European)", proficiency="native")],
        job_histories=[],
        skills=[],
    )
    reqs = _requirements((RequirementKind.LANGUAGE, "european portuguese"))

    report = build_match_report(profile_with_pt_pt, reqs, reference_date=reference_date)

    assert report.matches[0].status is MatchStatus.MATCHED
