"""Criterion 19: a validator rejects a generated CV that contains (a) a bullet with no
source id, (b) an employer/title/date/credential absent from the profile, or (c) a numeric
claim whose value is not present in its source bullet's metrics. Rejection always names the
offending line. See ADR 0004 decision 7 for the concrete numeric-claim algorithm and its
worked examples, which the tests below reproduce.
"""

from datetime import date

import pytest

from cv_writer.generation.models import (
    ExtraInput,
    ExtraInputKind,
    GeneratedBulletDraft,
    RephraseOutput,
)
from cv_writer.generation.validator import extract_numeric_tokens, validate_generated_cv
from cv_writer.profile.models import Bullet, Identity, JobHistory, Metric, Profile


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
            Bullet(
                id="job-acme-b2",
                situation="S2",
                task="T2",
                action="A2",
                result="R2",
                # no metric — any numeric claim citing this bullet must be rejected.
            ),
            Bullet(id="job-acme-b3", situation="S3", task="T3", action="A3", result="R3"),
        ],
    )
    return Profile(
        identity=Identity(name="Ana Example", email="ana@example.com"),
        job_histories=[history],
        skills=[],
    )


@pytest.fixture
def extra_inputs() -> list[ExtraInput]:
    return [ExtraInput(id="extra-1", kind=ExtraInputKind.EMPHASIS, text="Emphasize backend work")]


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("Cut p99 latency by 77%, from 1.4s to 320ms.", ["77%", "1.4s", "320ms"]),
        ("Reduced onboarding time by 3x.", ["3x"]),
        ("No numbers here at all.", []),
    ],
)
def test_extract_numeric_tokens(text, expected):
    tokens = extract_numeric_tokens(text)

    for value in expected:
        assert value in tokens


def test_bullet_with_no_source_id_is_rejected_naming_the_line(profile, extra_inputs):
    draft = RephraseOutput(
        bullets=[GeneratedBulletDraft(text="Cut latency significantly.", source_id="")]
    )

    failures = validate_generated_cv(draft, profile, extra_inputs)

    assert len(failures) == 1
    assert "source id" in failures[0].reason.lower()
    assert failures[0].offending_line == "Cut latency significantly."


def test_bullet_naming_an_employer_absent_from_the_profile_is_rejected(profile, extra_inputs):
    draft = RephraseOutput(
        bullets=[
            GeneratedBulletDraft(
                text="Cut checkout latency at Initech by 50%.", source_id="job-acme-b1"
            )
        ]
    )

    failures = validate_generated_cv(draft, profile, extra_inputs)

    assert len(failures) == 1
    assert "initech" in failures[0].reason.lower()


def test_bullet_naming_the_true_employer_passes_the_entity_check(profile, extra_inputs):
    draft = RephraseOutput(
        bullets=[
            GeneratedBulletDraft(
                text="Cut checkout p99 latency by 77%, from 1.4s to 320ms, at Acme Corp.",
                source_id="job-acme-b1",
            )
        ]
    )

    failures = validate_generated_cv(draft, profile, extra_inputs)

    assert failures == []


def test_numeric_claim_matching_its_source_metric_passes(profile, extra_inputs):
    draft = RephraseOutput(
        bullets=[
            GeneratedBulletDraft(
                text="Cut checkout p99 latency by 77%, from 1.4s to 320ms.",
                source_id="job-acme-b1",
            )
        ]
    )

    failures = validate_generated_cv(draft, profile, extra_inputs)

    assert failures == []


def test_numeric_claim_not_in_its_source_metric_is_rejected_naming_line_and_token(
    profile, extra_inputs
):
    draft = RephraseOutput(
        bullets=[
            GeneratedBulletDraft(
                text="Cut checkout p99 latency by 80%, from 1.4s to 320ms.",
                source_id="job-acme-b1",
            )
        ]
    )

    failures = validate_generated_cv(draft, profile, extra_inputs)

    assert len(failures) == 1
    assert "80%" in failures[0].reason
    assert failures[0].offending_line == "Cut checkout p99 latency by 80%, from 1.4s to 320ms."


def test_any_numeric_claim_against_a_metric_less_bullet_is_rejected(profile, extra_inputs):
    draft = RephraseOutput(
        bullets=[
            GeneratedBulletDraft(text="Reduced onboarding time by 3x.", source_id="job-acme-b2")
        ]
    )

    failures = validate_generated_cv(draft, profile, extra_inputs)

    assert len(failures) == 1
    assert "3x" in failures[0].reason


def test_numeric_claim_from_an_extra_input_source_is_always_rejected(profile, extra_inputs):
    draft = RephraseOutput(
        bullets=[GeneratedBulletDraft(text="Improved throughput by 40%.", source_id="extra-1")]
    )

    failures = validate_generated_cv(draft, profile, extra_inputs)

    assert len(failures) == 1
    assert "40%" in failures[0].reason


def test_bullet_mentioning_a_skill_after_with_is_not_flagged_as_an_unknown_entity(
    profile, extra_inputs
):
    # Regression: the entity check used to fire on "with"/"for"/"na"/"no"/"em", so ordinary
    # CV prose mentioning a tool or team ("worked with Python and SQL daily") was wrongly
    # rejected as a fabricated employer. Narrowed to "at" only (validator.py).
    draft = RephraseOutput(
        bullets=[
            GeneratedBulletDraft(
                text="Worked with Python and SQL daily, partnered with Marketing on launches.",
                source_id="job-acme-b3",
            )
        ]
    )

    failures = validate_generated_cv(draft, profile, extra_inputs)

    assert failures == []


def test_fabricated_number_that_is_a_substring_of_the_true_metric_is_still_rejected(
    profile, extra_inputs
):
    # Regression: plain substring containment let "7%" pass because it's a substring of the
    # true "-77%", and would let "20ms" pass as a substring of "320ms" — both are numbers
    # that were never actually claimed by the source metric.
    draft = RephraseOutput(
        bullets=[
            GeneratedBulletDraft(
                text="Brought checkout latency down to 20ms flat.", source_id="job-acme-b1"
            )
        ]
    )

    failures = validate_generated_cv(draft, profile, extra_inputs)

    assert len(failures) == 1
    assert "20ms" in failures[0].reason


def test_technical_terms_with_embedded_digits_are_not_treated_as_numeric_claims(
    profile, extra_inputs
):
    # Regression: extract_numeric_tokens() used to pull "99" out of "p99" (no word-boundary
    # guard), rejecting truthful bullets that use ordinary tech jargon near a source bullet
    # whose metric doesn't happen to contain that same digit fragment.
    draft = RephraseOutput(
        bullets=[
            GeneratedBulletDraft(
                text="Debugged a tricky p99 latency spike.", source_id="job-acme-b2"
            )
        ]
    )

    failures = validate_generated_cv(draft, profile, extra_inputs)

    assert failures == []


def test_direction_reversed_claim_is_rejected_even_though_the_number_matches(
    profile, extra_inputs
):
    # Regression: the source metric is a decrease (-77%); a bullet claiming an *increase* of
    # the same magnitude used to pass, since "77%" is a substring of "-77%" either way —
    # digit matching alone can't see that the claimed direction is reversed.
    draft = RephraseOutput(
        bullets=[
            GeneratedBulletDraft(
                text="Increased checkout p99 latency by 77%, ironically.",
                source_id="job-acme-b1",
            )
        ]
    )

    failures = validate_generated_cv(draft, profile, extra_inputs)

    assert len(failures) == 1
    assert "direction" in failures[0].reason.lower()


def test_bullet_naming_an_employer_matching_the_profile_loosely_is_accepted(
    profile, extra_inputs
):
    # Regression: an exact-string entity match rejected "at Acme Corp" style names that
    # legitimately vary from the profile's own text (e.g. a trailing ", Inc." the profile
    # doesn't include, or vice versa) — normalized/substring comparison fixes this.
    draft = RephraseOutput(
        bullets=[
            GeneratedBulletDraft(
                text="Shipped the fraud pipeline at Acme.", source_id="job-acme-b3"
            )
        ]
    )

    failures = validate_generated_cv(draft, profile, extra_inputs)

    assert failures == []


def test_bullet_citing_an_unknown_source_id_is_rejected(profile, extra_inputs):
    draft = RephraseOutput(
        bullets=[GeneratedBulletDraft(text="Did great work.", source_id="does-not-exist")]
    )

    failures = validate_generated_cv(draft, profile, extra_inputs)

    assert len(failures) == 1
    assert "does-not-exist" in failures[0].reason


def test_multiple_bullets_can_each_produce_their_own_failure(profile, extra_inputs):
    draft = RephraseOutput(
        bullets=[
            GeneratedBulletDraft(text="Cut latency by 80%.", source_id="job-acme-b1"),
            GeneratedBulletDraft(text="Did fine work.", source_id=""),
        ]
    )

    failures = validate_generated_cv(draft, profile, extra_inputs)

    assert len(failures) == 2
