"""Extract a structured requirement set from posting text (criterion 12).

Curated dictionaries + regex phrase matching, no NLP/LLM (ADR 0003, spec open question 4: this
starts deterministic and may graduate to LLM-assisted extraction later, human-confirmed, without
touching criterion 14's determinism for *scoring*). Every matched requirement keeps the verbatim
substring of the posting text it came from as `source_phrase`, so a human can always see why the
tool believes a requirement is there — the extractor is a curated list, not an oracle.

Required vs. preferred skills (criterion 12) are distinguished by which section of the posting a
skill phrase falls in: text is split into "required" / "preferred" zones by scanning for the
section markers in _REQUIRED_SECTION_MARKERS / _PREFERRED_SECTION_MARKERS, defaulting to
"required" until (if ever) a preferred marker is seen. This is a heuristic, not a guarantee —
flagged in ADR 0003 as one to watch against real postings.
"""

from __future__ import annotations

import re
from functools import cache

from .models import Requirement, RequirementKind, RequirementSet

# canonical value -> phrases that count as a match. Order doesn't affect the result (the final
# list is sorted before being returned) but keeps this list human-scannable.
SKILL_TERMS: dict[str, list[str]] = {
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
    # Added 2026-08-19 for a real Lidl (Spain) posting during operational-readiness testing —
    # the dictionary above was entirely software-engineering terms (a leftover from the spec's
    # example "Backend Engineer" persona) and had zero coverage for a non-engineering profile.
    # Canonical keys are chosen to textually match this profile's actual skill names (see
    # matching/matcher.py::_skill_name_matches) so real matches succeed; phrases are the actual
    # Spanish wording from the posting. Scoped, ad hoc widening — see the follow-up spec note in
    # docs/handoff-operational-readiness.md for the general fix (a data-driven term list, same
    # shape as the PT-PT brasileirismos checker, instead of a hardcoded Python dict).
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

SENIORITY_TERMS: dict[str, list[str]] = {
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

LANGUAGE_TERMS: dict[str, list[str]] = {
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

WORK_MODEL_TERMS: dict[str, list[str]] = {
    "remote": ["fully remote", "remote", "work from home", "wfh"],
    "hybrid": ["hybrid"],
    "onsite": ["on-site", "onsite", "in-office", "in office"],
    "relocation": ["relocation", "relocate", "visa sponsorship", "sponsorship"],
}

_REQUIRED_SECTION_MARKERS = (
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
_PREFERRED_SECTION_MARKERS = (
    "nice to have",
    "nice-to-have",
    "preferred",
    "preferred qualifications",
    "bonus points",
    "a plus",
    "would be a plus",
    "good to have",
    "pluses",
    # Added 2026-08-19 alongside the SKILL_TERMS widening above — see that comment.
    "se valorará",
)


def extract_requirements(text: str) -> RequirementSet:
    """Extract required/preferred skills, seniority, language, and work-model requirements
    from posting text. Pure function, no I/O — the "no LLM call" half of criterion 14."""
    zones = _skill_zones(text)

    requirements: list[Requirement] = []
    requirements.extend(_match_skills(text, zones))
    requirements.extend(_match_terms(text, SENIORITY_TERMS, RequirementKind.SENIORITY))
    requirements.extend(_match_terms(text, LANGUAGE_TERMS, RequirementKind.LANGUAGE))
    requirements.extend(
        _match_terms(text, WORK_MODEL_TERMS, RequirementKind.LOCATION_WORK_MODEL)
    )

    requirements.sort(key=lambda r: (r.kind.value, r.value))
    return RequirementSet(requirements=requirements)


def _skill_zones(text: str) -> list[tuple[int, str]]:
    """Return [(char_offset, zone)] boundaries, `zone` one of "required"/"preferred", sorted
    by offset. The zone in effect at a given offset is the last boundary at or before it,
    defaulting to "required" before the first boundary.

    Preferred markers are found first, and a required-marker match is dropped if it falls
    *inside* a preferred marker's own matched span — otherwise a heading like "Preferred
    Qualifications" (which contains the required-marker word "qualifications") would plant a
    required-zone boundary a few characters after its own preferred-zone boundary, silently
    reverting to "required" for everything under that heading.
    """
    lowered = text.lower()

    preferred_spans: list[tuple[int, int]] = []
    for marker in _PREFERRED_SECTION_MARKERS:
        for match in re.finditer(re.escape(marker), lowered):
            preferred_spans.append((match.start(), match.end()))

    boundaries: list[tuple[int, str]] = [(0, "required")]
    boundaries.extend((start, "preferred") for start, _end in preferred_spans)

    for marker in _REQUIRED_SECTION_MARKERS:
        for match in re.finditer(re.escape(marker), lowered):
            start = match.start()
            if any(p_start <= start < p_end for p_start, p_end in preferred_spans):
                continue
            boundaries.append((start, "required"))

    boundaries.sort(key=lambda b: b[0])
    return boundaries


def _zone_at(zones: list[tuple[int, str]], offset: int) -> str:
    current = "required"
    for boundary_offset, zone in zones:
        if boundary_offset > offset:
            break
        current = zone
    return current


def _match_skills(text: str, zones: list[tuple[int, str]]) -> list[Requirement]:
    matches: list[Requirement] = []
    for value, phrases in SKILL_TERMS.items():
        match = _first_phrase_match(text, phrases)
        if match is None:
            continue
        zone = _zone_at(zones, match.start())
        kind = (
            RequirementKind.PREFERRED_SKILL
            if zone == "preferred"
            else RequirementKind.REQUIRED_SKILL
        )
        matches.append(
            Requirement(kind=kind, value=value, source_phrase=match.group(0).strip())
        )
    return matches


def _match_terms(
    text: str, dictionary: dict[str, list[str]], kind: RequirementKind
) -> list[Requirement]:
    matches: list[Requirement] = []
    for value, phrases in dictionary.items():
        match = _first_phrase_match(text, phrases)
        if match is not None:
            matches.append(
                Requirement(kind=kind, value=value, source_phrase=match.group(0).strip())
            )
    return matches


@cache
def word_boundary_pattern(phrase: str) -> re.Pattern[str]:
    """A case-insensitive pattern matching `phrase` only on word boundaries — "sql" won't
    match inside "postgresql", "git" won't match inside "github". Cached (patterns never
    change at runtime) and shared with matching/ranking.py and matching/matcher.py so every
    phrase/skill-name comparison in the codebase uses the same boundary rule."""
    return re.compile(rf"(?<![A-Za-z0-9]){re.escape(phrase.strip())}(?![A-Za-z0-9])", re.IGNORECASE)


def _first_phrase_match(text: str, phrases: list[str]) -> re.Match[str] | None:
    for phrase in phrases:
        match = word_boundary_pattern(phrase).search(text)
        if match is not None:
            return match
    return None
