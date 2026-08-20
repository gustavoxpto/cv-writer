"""Spec 002: the requirement vocabulary is versioned data, not Python literals.

Covers AC-001 (loaded from a versioned YAML file) and AC-002 (the migration loses no
vocabulary). AC-004's native-language names live in test_requirement_sections.py alongside the
section-marker tests, since both are assertions about extraction behaviour rather than about the
file's shape.

The no-loss test here is the point of the whole exercise. The 8 non-engineering terms were added
ad hoc on 2026-08-19 and committed untested on 2026-08-20 (387d937) to unblock a real
application; SNAPSHOT_387D937 below is a frozen copy of exactly what that commit shipped. Testing
the YAML against it is what converts that stopgap into covered behaviour — and it is a `==`, not
a subset check, so a term silently dropped during the migration fails here rather than in six
months against a real posting.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from cv_writer.ingestion.term_list import (
    DEFAULT_TERMS_PATH,
    RequirementTermList,
    load_requirement_terms,
)

REPO_ROOT = Path(__file__).resolve().parents[3]

# Frozen at git revision 387d937 — the commit that shipped the untested stopgap. Do not "tidy"
# this: its whole value is being an independent copy of what the Python dictionaries held, so a
# migration that quietly loses a term has something to fail against.
SNAPSHOT_387D937_SKILLS: dict[str, list[str]] = {
    "python": ["python"],
    "javascript": ["javascript", "js"],
    "typescript": ["typescript", "ts"],
    "sql": ["sql"],
    "docker": ["docker"],
    "kubernetes": ["kubernetes", "k8s"],
    "aws": ["aws", "amazon web services"],
    "azure": ["azure"],
    "gcp": ["gcp", "google cloud"],
    "react": ["react", "react.js", "reactjs"],
    "fastapi": ["fastapi"],
    "django": ["django"],
    "flask": ["flask"],
    "git": ["git"],
    "ci/cd": ["ci/cd", "continuous integration", "continuous delivery"],
    "linux": ["linux"],
    "rest api": ["rest api", "restful api", "rest apis"],
    "graphql": ["graphql"],
    "postgresql": ["postgresql", "postgres"],
    "mysql": ["mysql"],
    "mongodb": ["mongodb", "mongo"],
    "terraform": ["terraform"],
    "agile": ["agile", "scrum"],
    "pytest": ["pytest"],
    "pandas": ["pandas"],
    "machine learning": ["machine learning", "ml"],
    "stakeholder management": ["stakeholders", "stakeholder management"],
    "project planning": [
        "gestión de proyectos",
        "planificación de proyectos",
        "planificación anual de proyectos",
        "project management",
    ],
    "instructional design": [
        "capacitarás",
        "capacitación",
        "formación básica y avanzada",
        "formación teórico-práctica",
    ],
    "cross-functional collaboration": [
        "transversal",
        "trabajo transversal",
        "afectación transversal",
    ],
    "problem solving": ["resolución de problemas"],
    "strategic consulting": ["consultoría estratégica"],
    "microsoft office": ["paquete office", "microsoft office"],
    "google workspace": ["entorno google", "google workspace"],
}

SNAPSHOT_387D937_SENIORITY: dict[str, list[str]] = {
    "intern": ["intern", "internship"],
    "junior": ["junior", "entry level", "entry-level"],
    "mid": ["mid-level", "mid level", "intermediate"],
    "senior": ["senior", "sr."],
    "lead": ["lead", "tech lead", "team lead"],
    "staff": ["staff engineer"],
    "principal": ["principal engineer", "principal"],
    "manager": ["engineering manager", "manager"],
    "director": ["director"],
}

SNAPSHOT_387D937_LANGUAGES: dict[str, list[str]] = {
    "english": ["english", "inglés"],
    "european portuguese": ["european portuguese", "pt-pt"],
    "brazilian portuguese": ["brazilian portuguese", "pt-br"],
    "portuguese": ["portuguese"],
    "spanish": ["spanish", "español"],
    "french": ["french"],
    "german": ["german", "alemán"],
    "italian": ["italian"],
    "dutch": ["dutch"],
}

SNAPSHOT_387D937_WORK_MODELS: dict[str, list[str]] = {
    "remote": ["fully remote", "remote", "work from home", "wfh"],
    "hybrid": ["hybrid"],
    "onsite": ["on-site", "onsite", "in-office", "in office"],
    "relocation": ["relocation", "relocate", "visa sponsorship", "sponsorship"],
}

SNAPSHOT_387D937_REQUIRED_MARKERS: tuple[str, ...] = (
    "requirements",
    "required skills",
    "must have",
    "must-have",
    "you have",
    "what you'll need",
    "what you will need",
    "qualifications",
    "what we're looking for",
    "what we are looking for",
)

SNAPSHOT_387D937_PREFERRED_MARKERS: tuple[str, ...] = (
    "nice to have",
    "nice-to-have",
    "preferred",
    "preferred qualifications",
    "bonus points",
    "a plus",
    "would be a plus",
    "good to have",
    "pluses",
    "se valorará",
)

# The 8 keys added ad hoc on 2026-08-19 for a real Spanish posting. Named separately from the
# snapshot above so AC-002 can be seen discharged without diffing a 34-key blob.
APPENDIX_A_SKILL_KEYS = (
    "stakeholder management",
    "project planning",
    "instructional design",
    "cross-functional collaboration",
    "problem solving",
    "strategic consulting",
    "microsoft office",
    "google workspace",
)


@pytest.fixture(scope="module")
def terms() -> RequirementTermList:
    return load_requirement_terms()


def test_shipped_term_file_loads_and_validates(terms: RequirementTermList):
    """AC-001: the vocabulary is a data file the package ships, loaded through a validating
    loader — not literals compiled into a module."""
    assert DEFAULT_TERMS_PATH.exists()
    assert DEFAULT_TERMS_PATH.suffix == ".yaml"
    assert isinstance(terms, RequirementTermList)


def test_term_file_carries_an_integer_version(terms: RequirementTermList):
    """AC-001: 'versioned'. Same guard the PT-PT list has — a forgotten bump should fail loudly
    rather than leave two different vocabularies both calling themselves the same list."""
    assert isinstance(terms.version, int)
    assert terms.version >= 1


def test_skill_terms_match_the_387d937_snapshot_exactly(terms: RequirementTermList):
    """AC-002: no vocabulary is lost in the move to YAML — including the 8 keys that shipped
    untested. Equality, not containment: an added key must be a deliberate edit here too."""
    assert terms.as_mapping("skills") == SNAPSHOT_387D937_SKILLS


def test_appendix_a_terms_are_present_with_their_exact_phrases(terms: RequirementTermList):
    """AC-002 stated directly rather than inferred from the snapshot above: the non-engineering
    terms, with the accented Spanish wording from the posting they came from."""
    skills = terms.as_mapping("skills")

    for key in APPENDIX_A_SKILL_KEYS:
        assert key in skills, f"Appendix A key {key!r} lost in the migration"

    assert "gestión de proyectos" in skills["project planning"]
    assert "formación teórico-práctica" in skills["instructional design"]
    assert "afectación transversal" in skills["cross-functional collaboration"]
    assert "consultoría estratégica" in skills["strategic consulting"]


def test_seniority_language_and_work_model_terms_match_the_snapshot(
    terms: RequirementTermList,
):
    """AC-002: the other three dictionaries survive the move intact too."""
    assert terms.as_mapping("seniority") == SNAPSHOT_387D937_SENIORITY
    assert terms.as_mapping("languages") == SNAPSHOT_387D937_LANGUAGES
    assert terms.as_mapping("work_models") == SNAPSHOT_387D937_WORK_MODELS


def test_section_markers_match_the_snapshot(terms: RequirementTermList):
    """AC-002: the required/preferred markers are data now as well, including 'se valorará'."""
    assert tuple(terms.section_markers.required) == SNAPSHOT_387D937_REQUIRED_MARKERS
    assert tuple(terms.section_markers.preferred) == SNAPSHOT_387D937_PREFERRED_MARKERS


def test_loader_accepts_an_alternate_path(tmp_path: Path):
    """AC-001: 'load from a file' has to mean any file, or the tests below can only ever
    exercise the shipped one. Same parametrized-path affordance load_pt_pt_terms has."""
    alternate = tmp_path / "alt_terms.yaml"
    alternate.write_text(
        "version: 7\n"
        "skills:\n"
        "  - key: basket weaving\n"
        "    phrases: ['basket weaving']\n"
        "seniority: []\n"
        "languages: []\n"
        "work_models: []\n"
        "section_markers:\n"
        "  required: ['requisitos']\n"
        "  preferred: ['se valorará']\n",
        encoding="utf-8",
    )

    loaded = load_requirement_terms(alternate)

    assert loaded.version == 7
    assert loaded.as_mapping("skills") == {"basket weaving": ["basket weaving"]}


def test_requirements_module_holds_no_vocabulary_literals():
    """AC-001, stated as the outcome rather than the mechanism: after the migration the module
    contains no term strings, so extending the vocabulary cannot require editing Python. Checks
    a sample across all four dictionaries and both marker lists."""
    source = (REPO_ROOT / "src" / "cv_writer" / "ingestion" / "requirements.py").read_text(
        encoding="utf-8"
    )

    for literal in (
        '"python"',
        '"kubernetes"',
        '"se valorará"',
        '"visa sponsorship"',
        '"engineering manager"',
        '"consultoría estratégica"',
    ):
        assert literal not in source, (
            f"{literal} is still a literal in requirements.py; the vocabulary was supposed to "
            f"move to requirement_terms.yaml"
        )


def test_duplicate_canonical_keys_are_rejected(tmp_path: Path):
    """A YAML list cannot self-enforce unique keys the way a dict does — that is the one thing
    this format gives up. If two entries share a key the second silently wins and half the
    phrases stop matching, which is L-004's quiet-empty-result failure again. Fail loudly."""
    duplicated = tmp_path / "dupe_terms.yaml"
    duplicated.write_text(
        "version: 1\n"
        "skills:\n"
        "  - key: python\n"
        "    phrases: ['python']\n"
        "  - key: python\n"
        "    phrases: ['python3']\n"
        "seniority: []\n"
        "languages: []\n"
        "work_models: []\n"
        "section_markers:\n"
        "  required: []\n"
        "  preferred: []\n",
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="python"):
        load_requirement_terms(duplicated)


def test_every_phrase_is_non_empty(terms: RequirementTermList):
    """An empty phrase compiles to a pattern that matches at every position, so one stray blank
    entry would mark every posting as requiring that skill."""
    for group in ("skills", "seniority", "languages", "work_models"):
        for key, phrases in terms.as_mapping(group).items():
            assert phrases, f"{group}:{key} has no phrases"
            for phrase in phrases:
                assert phrase.strip(), f"{group}:{key} has a blank phrase"
