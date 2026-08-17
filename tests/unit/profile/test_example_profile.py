"""data/profile.example.yaml is the committed reference a human copies to
data/profile.yaml (open question 6) — it must always be schema-valid, or the
example is teaching people how to write an invalid profile."""

from pathlib import Path

from cv_writer.profile import load_profile

EXAMPLE_PROFILE = Path(__file__).parents[3] / "data" / "profile.example.yaml"


def test_example_profile_is_valid():
    profile = load_profile(EXAMPLE_PROFILE)

    assert profile.identity.name
    assert profile.job_histories
    assert profile.skills
