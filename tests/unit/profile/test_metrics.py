"""Criterion 4: every job history carries at least one quantified metric across its
bullets, stored as structured data on the bullet whose result it belongs to. A history
with no metric anywhere fails validation, naming the history. profile_check() additionally
(and non-fatally) flags a history where only one of several bullets is quantified."""

from pathlib import Path

import pytest

from cv_writer.profile import ProfileValidationError, load_profile, profile_check

FIXTURES = Path(__file__).parent / "fixtures"


def test_metric_is_structured_data_on_the_bullet_it_belongs_to():
    profile = load_profile(FIXTURES / "valid_profile.yaml")
    quantified_bullet = profile.job_histories[0].bullets[0]

    assert quantified_bullet.metric is not None
    assert quantified_bullet.metric.value == "-77%"
    assert quantified_bullet.metric.unit == "p99 latency"


def test_individual_bullets_may_be_qualitative():
    profile = load_profile(FIXTURES / "valid_profile.yaml")
    qualitative_bullet = profile.job_histories[0].bullets[2]

    assert qualitative_bullet.metric is None


def test_history_with_no_metric_anywhere_fails_validation_naming_the_history():
    with pytest.raises(ProfileValidationError) as exc_info:
        load_profile(FIXTURES / "no_metric_history.yaml")

    message = str(exc_info.value)
    assert "job-no-metric" in message


def test_history_with_only_one_of_several_bullets_quantified_still_loads():
    # Doesn't fail — it's a check-time nudge, not a load-time rejection.
    profile = load_profile(FIXTURES / "single_quantified_bullet.yaml")
    assert len(profile.job_histories) == 1


def test_profile_check_flags_history_with_only_one_quantified_bullet():
    profile = load_profile(FIXTURES / "single_quantified_bullet.yaml")
    warnings = profile_check(profile)

    matching = [w for w in warnings if w.kind == "single_quantified_bullet"]
    assert len(matching) == 1
    assert matching[0].subject == "job-one-metric"


def test_profile_check_does_not_flag_a_well_evidenced_history():
    profile = load_profile(FIXTURES / "valid_profile.yaml")
    warnings = profile_check(profile)

    assert [w for w in warnings if w.kind == "single_quantified_bullet"] == []
