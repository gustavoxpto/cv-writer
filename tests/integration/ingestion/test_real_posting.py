"""Spec 002 AC-005: the extractor works against a real posting, not only against fixtures we
wrote ourselves.

This is the test the whole feature exists for. On 2026-08-19 this advert produced exactly one
requirement — a seniority signal — and generation then failed with "no evidence available to
generate a CV from": not because the profile was empty, but because extraction had surfaced
nothing to match it against (.specs/LESSONS.md L-004).

AC-005a is why the fixture is real text rather than something assembled from the term file. The
direction of derivation matters: the vocabulary in requirement_terms.yaml was taken FROM this
posting, so this test asks whether that vocabulary handles the text it came from. A fixture
written out of the dictionary would assert only that the dictionary matches itself, which is the
one thing we already know.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from cv_writer.ingestion.models import RequirementKind, RequirementSet
from cv_writer.ingestion.requirements import extract_requirements
from cv_writer.ingestion.term_list import load_requirement_terms

FIXTURE = Path(__file__).parent / "fixtures" / "posting_es_redacted.txt"


def _posting_text() -> str:
    """The fixture minus its provenance header — '#' lines are commentary, not posting text."""
    raw = FIXTURE.read_text(encoding="utf-8")
    return "\n".join(line for line in raw.splitlines() if not line.startswith("#"))


@pytest.fixture(scope="module")
def extracted() -> RequirementSet:
    return extract_requirements(_posting_text())


def test_the_real_posting_yields_more_than_one_requirement(extracted: RequirementSet):
    """AC-005, stated as the spec states it. The bar is deliberately also stated a second way:
    'more than one' was true of the broken behaviour plus a single lucky match, so the second
    assertion pins what actually changed — one requirement became eleven."""
    assert len(extracted.requirements) > 1
    assert len(extracted.requirements) >= 10


def test_the_posting_requirements_are_the_ones_a_human_would_name(extracted: RequirementSet):
    """AC-005: not noise. These are the skills the advert actually asks for, read off the
    Spanish text by hand — project management, consulting, training, cross-team work, problem
    solving, and the two office suites it names as alternatives."""
    required = {r.value for r in extracted.of_kind(RequirementKind.REQUIRED_SKILL)}

    assert {
        "project planning",
        "strategic consulting",
        "instructional design",
        "cross-functional collaboration",
        "problem solving",
        "microsoft office",
        "google workspace",
    } <= required


def test_the_posting_languages_and_seniority_are_extracted(extracted: RequirementSet):
    """AC-004 against real text: the advert asks for C1 English, advanced Spanish and values
    German, each named in Spanish. AC-005 for the seniority signal that was the *only* thing the
    broken extractor found."""
    languages = {r.value for r in extracted.of_kind(RequirementKind.LANGUAGE)}
    seniority = {r.value for r in extracted.of_kind(RequirementKind.SENIORITY)}

    assert {"english", "spanish", "german"} <= languages
    assert "senior" in seniority


def test_source_phrases_quote_the_posting_verbatim_with_accents(extracted: RequirementSet):
    """Criterion 12's promise — a human can see the exact words behind every requirement — has to
    survive accented Spanish. Reporting 'german' against text that said 'alemán' would break the
    audit trail this tool is built on."""
    by_value = {r.value: r.source_phrase for r in extracted.requirements}

    assert by_value["german"] == "alemán"
    assert by_value["english"] == "inglés"
    assert by_value["project planning"] == "gestión de proyectos"
    assert by_value["problem solving"] == "resolución de problemas"

    posting = _posting_text()
    for phrase in by_value.values():
        assert phrase in posting, f"source_phrase {phrase!r} is not verbatim in the posting"


def test_the_fixture_is_real_prose_and_not_written_from_the_term_file():
    """AC-005a as a sensor rather than an inspection.

    The verifier flagged at contract-signing that provenance was the one Check only a human could
    settle. This narrows that: a fixture assembled from the term file would consist largely of
    phrases the term file contains. Real posting prose is mostly sentences the vocabulary has
    never heard of. Asserting that most of the fixture's words appear in no phrase of the term
    list will not prove authorship, but it does fail loudly on the specific cheat AC-005a forbids.
    """
    terms = load_requirement_terms()
    vocabulary: set[str] = set()
    for group in ("skills", "seniority", "languages", "work_models"):
        for phrases in terms.as_mapping(group).values():
            vocabulary.update(word.lower() for phrase in phrases for word in phrase.split())
    vocabulary.update(
        word.lower()
        for marker in (*terms.section_markers.required, *terms.section_markers.preferred)
        for word in marker.split()
    )

    words = [w.strip(".,;:()¿?¡!/").lower() for w in _posting_text().split()]
    words = [w for w in words if len(w) > 3]
    unknown = [w for w in words if w not in vocabulary]

    assert len(unknown) / len(words) > 0.8, (
        "most of this fixture's words are in the term file — that is what a fixture written out "
        "of the dictionary looks like, and AC-005a forbids it"
    )


def test_extraction_of_the_real_posting_is_repeatable(extracted: RequirementSet):
    """Criterion 14 against the real input: same text in, same requirements out."""
    again = extract_requirements(_posting_text())

    assert [(r.kind, r.value, r.source_phrase) for r in again.requirements] == [
        (r.kind, r.value, r.source_phrase) for r in extracted.requirements
    ]
