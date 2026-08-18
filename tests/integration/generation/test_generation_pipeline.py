"""Criteria 17-23: end-to-end generate_cv() — rephrase (behind the bounded Rephraser
interface, criterion 22) -> anti-fabrication validation (criterion 19) -> PT-PT check
(criterion 21) -> language refusal (criterion 20) -> accept. Always exercised with
FakeRephraser — never touches the network or a real API key (criterion 22)."""

from datetime import date, datetime, timezone

import pytest

from cv_writer.generation.models import (
    ExtraInput,
    ExtraInputKind,
    GeneratedBulletDraft,
    GeneratedCv,
    GenerationFailure,
    RephraseOutput,
)
from cv_writer.generation.pipeline import generate_cv
from cv_writer.generation.rephraser import FakeRephraser
from cv_writer.ingestion.models import Posting, Requirement, RequirementKind
from cv_writer.matching.models import EvidenceBullet, MatchReport, MatchStatus, RequirementMatch
from cv_writer.profile.models import Bullet, Identity, JobHistory, Language, Metric, Profile


@pytest.fixture
def profile() -> Profile:
    history = JobHistory(
        id="job-acme",
        company="Acme Corp",
        role_title="Backend Engineer",
        country="Portugal",
        area="Engineering",
        start_date=date(2020, 1, 15),
        end_date="present",
        bullets=[
            Bullet(
                id="job-acme-b1",
                situation="Checkout API had frequent timeouts under peak load.",
                task="Bring p99 latency under the 500ms SLA.",
                action="Profiled the request path and added a read-through cache.",
                result="Cut p99 latency from 1.4s to 320ms.",
                metric=Metric(value="-77%", unit="p99 latency", baseline="from 1.4s to 320ms"),
            ),
            Bullet(id="job-acme-b2", situation="S2", task="T2", action="A2", result="R2"),
            Bullet(id="job-acme-b3", situation="S3", task="T3", action="A3", result="R3"),
        ],
    )
    return Profile(
        identity=Identity(name="Ana Example", email="ana@example.com"),
        languages=[Language(name="English", proficiency="professional")],
        job_histories=[history],
        skills=[],
    )


@pytest.fixture
def posting() -> Posting:
    return Posting(
        raw_text="We are looking for a senior backend engineer with our team.",
        source="https://example.com/job",
        fetched_at=datetime.now(timezone.utc),
        ingestion_tier=1,
    )


@pytest.fixture
def match_report() -> MatchReport:
    match = RequirementMatch(
        requirement=Requirement(
            kind=RequirementKind.REQUIRED_SKILL, value="python", source_phrase="Python"
        ),
        status=MatchStatus.MATCHED,
        evidence_skill="Python",
        evidence_bullets=[EvidenceBullet(history_id="job-acme", bullet_index=0, rank_score=1)],
    )
    return MatchReport(matches=[match], score=100.0, score_formula="test")


def test_generate_cv_with_fake_rephraser_accepts_a_truthful_cv(profile, posting, match_report):
    result = generate_cv(
        profile=profile,
        posting=posting,
        match_report=match_report,
        extra_inputs=[],
        rephraser=FakeRephraser(),
    )

    assert isinstance(result, GeneratedCv)
    assert result.language == "english"
    assert "job-acme-b1" in result.source_ids_used


def test_generate_cv_rejects_a_fabricated_numeric_claim_from_the_fake_llm(
    profile, posting, match_report
):
    fabricated = RephraseOutput(
        bullets=[
            GeneratedBulletDraft(
                text="Cut checkout p99 latency by 999%, an industry record.",
                source_id="job-acme-b1",
            )
        ]
    )

    result = generate_cv(
        profile=profile,
        posting=posting,
        match_report=match_report,
        extra_inputs=[],
        rephraser=FakeRephraser(fixed_response=fabricated),
    )

    assert isinstance(result, GenerationFailure)
    assert len(result.validation_failures) == 1
    assert "999%" in result.validation_failures[0].reason


def test_generate_cv_refuses_a_language_not_in_the_profile(profile, match_report):
    german_posting = Posting(
        raw_text="Wir suchen einen erfahrenen Softwareentwickler fuer unser Team.",
        source="https://example.com/job",
        fetched_at=datetime.now(timezone.utc),
        ingestion_tier=1,
    )

    result = generate_cv(
        profile=profile,
        posting=german_posting,
        match_report=match_report,
        extra_inputs=[],
        rephraser=FakeRephraser(),
    )

    assert isinstance(result, GenerationFailure)
    assert result.reason


def test_generate_cv_blocks_acceptance_on_a_pt_pt_violation(match_report):
    pt_profile = Profile(
        identity=Identity(name="Ana Example", email="ana@example.com"),
        languages=[Language(name="Portuguese", proficiency="native")],
        job_histories=[
            JobHistory(
                id="job-acme",
                company="Acme Corp",
                role_title="Backend Engineer",
                country="Portugal",
                area="Engineering",
                start_date=date(2020, 1, 15),
                end_date="present",
                bullets=[
                    Bullet(
                        id="job-acme-b1",
                        situation="S1",
                        task="T1",
                        action="A1",
                        result="Geri o time no meu celular.",
                        metric=Metric(value="+10%"),
                    ),
                    Bullet(id="job-acme-b2", situation="S2", task="T2", action="A2", result="R2"),
                    Bullet(id="job-acme-b3", situation="S3", task="T3", action="A3", result="R3"),
                ],
            )
        ],
        skills=[],
    )
    pt_posting = Posting(
        raw_text="Procuramos um engenheiro backend para a nossa equipa em Portugal.",
        source="https://example.com/job",
        fetched_at=datetime.now(timezone.utc),
        ingestion_tier=1,
        country="Portugal",
    )

    result = generate_cv(
        profile=pt_profile,
        posting=pt_posting,
        match_report=match_report,
        extra_inputs=[],
        rephraser=FakeRephraser(),
    )

    assert isinstance(result, GenerationFailure)
    assert len(result.pt_pt_violations) >= 1


def test_generate_cv_includes_extra_input_bullets(profile, posting, match_report):
    extra = ExtraInput(id="extra-1", kind=ExtraInputKind.ACHIEVEMENT, text="Led a migration.")

    result = generate_cv(
        profile=profile,
        posting=posting,
        match_report=match_report,
        extra_inputs=[extra],
        rephraser=FakeRephraser(),
    )

    assert isinstance(result, GeneratedCv)
    assert "extra-1" in result.source_ids_used


def test_generate_cv_never_raises_on_a_stale_evidence_reference(profile, posting):
    # Regression: a code-review pass found _resolve_evidence_bullets() would raise an
    # uncaught IndexError on a stale bullet_index (e.g. match_report computed against a
    # profile snapshot that's since been edited) — violating generate_cv()'s own docstring
    # promise to never raise on a "normal" rejection. A dangling reference is now skipped.
    stale_match = RequirementMatch(
        requirement=Requirement(
            kind=RequirementKind.REQUIRED_SKILL, value="python", source_phrase="Python"
        ),
        status=MatchStatus.MATCHED,
        evidence_skill="Python",
        evidence_bullets=[EvidenceBullet(history_id="job-acme", bullet_index=99, rank_score=1)],
    )
    stale_report = MatchReport(matches=[stale_match], score=100.0, score_formula="test")

    result = generate_cv(
        profile=profile,
        posting=posting,
        match_report=stale_report,
        extra_inputs=[],
        rephraser=FakeRephraser(),
    )

    # No crash — an honest GenerationFailure, since the stale evidence contributes nothing.
    assert isinstance(result, GenerationFailure)
