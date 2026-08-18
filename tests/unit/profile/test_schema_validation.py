"""Criterion 1: profile.yaml loads into a validated Profile, or fails naming the field/path,
and never yields a partially-loaded profile."""

from pathlib import Path

import pytest
import yaml
from pydantic import ValidationError as PydanticValidationError

from cv_writer.profile import Profile, ProfileValidationError, load_profile, load_profile_dict

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


def test_non_utf8_file_fails_clearly_rather_than_crashing(tmp_path):
    # profile.yaml is meant to be hand-edited (data/profile.example.yaml says so), and an
    # editor that isn't UTF-8-aware can save accented characters as cp1252 instead. That
    # must fail as a clear ProfileValidationError, not an uncaught UnicodeDecodeError.
    bad_file = tmp_path / "profile.yaml"
    bad_file.write_bytes("identity:\n  location: Lisboa, n\xe3o utf8\n".encode("cp1252"))

    with pytest.raises(ProfileValidationError) as exc_info:
        load_profile(bad_file)

    assert "utf-8" in str(exc_info.value).lower()


def test_whitespace_only_required_field_fails_validation():
    # min_length=1 alone lets a single space through — it must be rejected the same as an
    # empty string, not silently loaded as "valid" STAR content.
    data = yaml.safe_load((FIXTURES / "valid_profile.yaml").read_text(encoding="utf-8"))
    data["job_histories"][0]["bullets"][0]["situation"] = " "

    with pytest.raises(ProfileValidationError) as exc_info:
        load_profile_dict(data)

    assert "situation" in str(exc_info.value)


def test_invalid_load_raises_via_pydantic_validation_which_never_partially_constructs():
    # "Never yields a partially-loaded profile" (criterion 1) holds because schema failures
    # route through Profile.model_validate(), which raises before constructing an instance
    # rather than building one field-by-field. Pinning the raised error's __cause__ to
    # pydantic's ValidationError asserts that mechanism directly, rather than just observing
    # that a local variable assignment didn't happen — which would hold true no matter how
    # load_profile is implemented internally, so didn't actually test the guarantee.
    with pytest.raises(ProfileValidationError) as exc_info:
        load_profile(FIXTURES / "missing_required_field.yaml")

    assert isinstance(exc_info.value.__cause__, PydanticValidationError)
