"""Criterion 5: skills are first-class records linked to the job histories that evidence
them. A skill claimed with no evidencing history loads fine but is flagged by profile_check()
as unevidenced. A skill's evidence must reference a real job history id."""

from pathlib import Path

import pytest

from cv_writer.profile import ProfileValidationError, load_profile, profile_check

FIXTURES = Path(__file__).parent / "fixtures"


def test_skill_is_a_first_class_record_linked_to_evidencing_histories():
    profile = load_profile(FIXTURES / "valid_profile.yaml")
    python_skill = next(s for s in profile.skills if s.name == "Python")

    assert python_skill.category == "language"
    assert python_skill.evidence == ["job-acme-2020", "job-globex-2022"]


def test_skill_with_no_evidence_loads_but_is_flagged_as_unevidenced():
    profile = load_profile(FIXTURES / "unevidenced_skill.yaml")
    rust_skill = next(s for s in profile.skills if s.name == "Rust")
    assert rust_skill.evidence == []

    warnings = profile_check(profile)
    matching = [w for w in warnings if w.kind == "unevidenced_skill"]
    assert len(matching) == 1
    assert matching[0].subject == "Rust"


def test_profile_check_does_not_flag_an_evidenced_skill():
    profile = load_profile(FIXTURES / "valid_profile.yaml")
    warnings = profile_check(profile)

    assert [w for w in warnings if w.kind == "unevidenced_skill"] == []


def test_skill_evidence_referencing_unknown_history_fails_validation():
    with pytest.raises(ProfileValidationError) as exc_info:
        load_profile(FIXTURES / "unresolved_skill_evidence.yaml")

    message = str(exc_info.value)
    assert "job-does-not-exist" in message
