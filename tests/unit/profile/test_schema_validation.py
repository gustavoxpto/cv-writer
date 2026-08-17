"""Criterion 1: profile.yaml loads into a validated Profile, or fails naming the field/path,
and never yields a partially-loaded profile."""

from pathlib import Path

import pytest

from cv_writer.profile import Profile, ProfileValidationError, load_profile

FIXTURES = Path(__file__).parent / "fixtures"


def test_valid_profile_loads_into_a_validated_profile_object():
    profile = load_profile(FIXTURES / "valid_profile.yaml")

    assert isinstance(profile, Profile)
    assert profile.identity.name == "Ana Example"
    assert profile.identity.email == "ana@example.com"
    assert len(profile.job_histories) == 2
    assert len(profile.skills) == 2


def test_missing_required_field_fails_naming_the_field_and_path():
    with pytest.raises(ProfileValidationError) as exc_info:
        load_profile(FIXTURES / "missing_required_field.yaml")

    message = str(exc_info.value)
    assert "identity" in message
    assert "email" in message


def test_malformed_yaml_fails_with_a_clear_error_not_a_crash():
    with pytest.raises(ProfileValidationError) as exc_info:
        load_profile(FIXTURES / "malformed_yaml.yaml")

    assert "not valid YAML" in str(exc_info.value)


def test_non_mapping_yaml_root_fails_clearly(tmp_path):
    bad_file = tmp_path / "list_root.yaml"
    bad_file.write_text("- just\n- a\n- list\n", encoding="utf-8")

    with pytest.raises(ProfileValidationError) as exc_info:
        load_profile(bad_file)

    assert "mapping" in str(exc_info.value)


def test_missing_file_fails_clearly_rather_than_crashing(tmp_path):
    with pytest.raises(ProfileValidationError):
        load_profile(tmp_path / "does_not_exist.yaml")


def test_invalid_load_never_leaves_a_partial_profile_bound_in_the_caller():
    # There's no "partial Profile" object to inspect by design: model_validate() either
    # returns a fully-validated instance or raises before constructing one. This test
    # documents that guarantee at the loader boundary rather than at the Pydantic boundary.
    profile = None
    try:
        profile = load_profile(FIXTURES / "missing_required_field.yaml")
    except ProfileValidationError:
        pass

    assert profile is None
