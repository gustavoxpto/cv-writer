"""Criterion 2: every job history entry has the required fields."""

from pathlib import Path

import pytest

from cv_writer.profile import ProfileValidationError, load_profile

FIXTURES = Path(__file__).parent / "fixtures"


def test_job_history_carries_the_required_fields():
    profile = load_profile(FIXTURES / "valid_profile.yaml")
    history = profile.job_histories[0]

    assert history.id == "job-acme-2020"
    assert history.company == "Acme Corp"
    assert history.role_title == "Backend Engineer"
    assert history.country == "Portugal"
    assert history.area == "Engineering"
    assert history.start_date.isoformat() == "2020-01-15"
    assert history.end_date.isoformat() == "2022-06-30"
    assert len(history.bullets) == 3


def test_job_history_end_date_accepts_the_literal_present():
    profile = load_profile(FIXTURES / "valid_profile.yaml")
    current_history = profile.job_histories[1]

    assert current_history.end_date == "present"


def test_duplicate_job_history_ids_fail_validation():
    with pytest.raises(ProfileValidationError) as exc_info:
        load_profile(FIXTURES / "duplicate_history_ids.yaml")

    assert "job-dup" in str(exc_info.value)


def test_end_date_before_start_date_fails_validation():
    with pytest.raises(ProfileValidationError) as exc_info:
        load_profile(FIXTURES / "inverted_date_range.yaml")

    assert "job-inverted-dates" in str(exc_info.value)
