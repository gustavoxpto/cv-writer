"""Criterion 18: every generated bullet carries the id of the profile bullet it was derived
from — which only works if bullet ids are unique across the whole profile, not just within one
job history. See ADR 0004 decision 1 for why a real `Bullet.id` field was added (rejecting both
the DB surrogate key and the `(history_id, bullet_index)` composite key as the stable citation
id) and why the uniqueness check is global, not per-history.
"""

from pathlib import Path

import pytest

from cv_writer.profile import ProfileValidationError, load_profile

FIXTURES = Path(__file__).parent / "fixtures"


def test_bullets_carry_a_stable_id():
    profile = load_profile(FIXTURES / "valid_profile.yaml")
    bullet = profile.job_histories[0].bullets[0]

    assert bullet.id == "job-acme-2020-b1"


def test_bullet_ids_are_unique_within_a_history():
    profile = load_profile(FIXTURES / "valid_profile.yaml")
    ids = [bullet.id for bullet in profile.job_histories[0].bullets]

    assert len(ids) == len(set(ids))


def test_duplicate_bullet_id_across_histories_fails_validation_naming_the_id():
    with pytest.raises(ProfileValidationError) as exc_info:
        load_profile(FIXTURES / "duplicate_bullet_ids.yaml")

    assert "shared-bullet-id" in str(exc_info.value)


def test_missing_bullet_id_fails_naming_the_field_and_path():
    with pytest.raises(ProfileValidationError) as exc_info:
        load_profile(FIXTURES / "missing_bullet_id.yaml")

    message = str(exc_info.value)
    assert "bullets" in message
    assert "id" in message


def test_purely_numeric_bullet_id_fails_validation():
    # Regression: a purely-digit id silently coerces to SQLite's INTEGER storage class in
    # application_bullet_sources.profile_bullet_id (ADR 0004 decision 1's declared-INTEGER
    # column), corrupting round-trip reads — rejected here, at the source.
    with pytest.raises(ProfileValidationError) as exc_info:
        load_profile(FIXTURES / "purely_numeric_bullet_id.yaml")

    assert "purely numeric" in str(exc_info.value)
