"""Criterion 3: each job history has 3-5 STAR bullets; outside that range, validation fails."""

from pathlib import Path

import pytest

from cv_writer.profile import ProfileValidationError, load_profile

FIXTURES = Path(__file__).parent / "fixtures"


def test_bullets_are_stored_as_explicit_star_fields():
    profile = load_profile(FIXTURES / "valid_profile.yaml")
    bullet = profile.job_histories[0].bullets[0]

    assert bullet.situation
    assert bullet.task
    assert bullet.action
    assert bullet.result


def test_fewer_than_three_bullets_fails_validation():
    with pytest.raises(ProfileValidationError) as exc_info:
        load_profile(FIXTURES / "bullet_count_too_few.yaml")

    assert "bullets" in str(exc_info.value)


def test_more_than_five_bullets_fails_validation():
    with pytest.raises(ProfileValidationError) as exc_info:
        load_profile(FIXTURES / "bullet_count_too_many.yaml")

    assert "bullets" in str(exc_info.value)
