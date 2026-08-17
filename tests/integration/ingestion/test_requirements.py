"""Criterion 12: extract required skills, preferred skills, seniority signals, language(s),
and location/work model from posting text, each keeping its verbatim source phrase."""

from cv_writer.ingestion.models import RequirementKind
from cv_writer.ingestion.requirements import extract_requirements

POSTING = """
Senior Backend Engineer — Remote (EU)

We are looking for a Senior Backend Engineer to join our platform team.

Requirements:
- 5+ years of experience with Python and SQL
- Experience with Docker and Kubernetes
- Fluent in English

Nice to have:
- Familiarity with GraphQL
- Experience with Terraform

This is a fully remote position; visa sponsorship is available for the right candidate.
"""


def test_extract_requirements_finds_required_skills_with_source_phrase():
    result = extract_requirements(POSTING)

    required = {r.value: r for r in result.of_kind(RequirementKind.REQUIRED_SKILL)}
    assert "python" in required
    assert "sql" in required
    assert "docker" in required
    assert "kubernetes" in required
    assert required["python"].source_phrase.lower() == "python"


def test_extract_requirements_finds_preferred_skills_separately_from_required():
    result = extract_requirements(POSTING)

    preferred = {r.value for r in result.of_kind(RequirementKind.PREFERRED_SKILL)}
    required = {r.value for r in result.of_kind(RequirementKind.REQUIRED_SKILL)}

    assert "graphql" in preferred
    assert "terraform" in preferred
    assert "graphql" not in required
    assert "terraform" not in required


def test_extract_requirements_finds_seniority_signal():
    result = extract_requirements(POSTING)

    seniority_values = {r.value for r in result.of_kind(RequirementKind.SENIORITY)}
    assert "senior" in seniority_values


def test_extract_requirements_finds_language():
    result = extract_requirements(POSTING)

    languages = {r.value for r in result.of_kind(RequirementKind.LANGUAGE)}
    assert "english" in languages


def test_extract_requirements_finds_location_work_model():
    result = extract_requirements(POSTING)

    work_model = {r.value for r in result.of_kind(RequirementKind.LOCATION_WORK_MODEL)}
    assert "remote" in work_model
    assert "relocation" in work_model


def test_extract_requirements_is_deterministic():
    first = extract_requirements(POSTING)
    second = extract_requirements(POSTING)

    assert first.model_dump() == second.model_dump()


def test_extract_requirements_finds_nothing_it_shouldnt_invent():
    result = extract_requirements("We are a small bakery looking for a friendly cashier.")

    values = {r.value for r in result.requirements}
    assert "python" not in values
    assert "senior" not in values


def test_preferred_qualifications_heading_does_not_flip_back_to_required():
    # Regression: "qualifications" (a required-section marker) is a substring of "preferred
    # qualifications" itself — a naive zone scan plants a required-zone boundary a few chars
    # after the preferred one, misclassifying everything under this very common heading.
    text = "Requirements:\n- Docker\n\nPreferred Qualifications:\n- GraphQL\n- Terraform"

    result = extract_requirements(text)

    preferred = {r.value for r in result.of_kind(RequirementKind.PREFERRED_SKILL)}
    required = {r.value for r in result.of_kind(RequirementKind.REQUIRED_SKILL)}
    assert preferred == {"graphql", "terraform"}
    assert required == {"docker"}
