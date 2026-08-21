"""Extract a structured requirement set from posting text (criterion 12).

A curated, versioned term file + regex phrase matching, no NLP/LLM (ADR 0003, spec open
question 4: this starts deterministic and may graduate to LLM-assisted extraction later,
human-confirmed, without touching criterion 14's determinism for *scoring*). Every matched
requirement keeps the verbatim substring of the posting text it came from as `source_phrase`, so
a human can always see why the tool believes a requirement is there — the extractor is a curated
list, not an oracle.

The vocabulary itself is data, not code: data/requirement_terms.yaml, loaded and validated by
term_list.py (spec 002 AC-001). This module holds the matching logic and nothing else.

Required vs. preferred skills (criterion 12) are distinguished by which section of the posting a
skill phrase falls in: text is split into "required" / "preferred" zones by scanning for the
section markers loaded from that file, defaulting to "required" until (if ever) a preferred
marker is seen. This is a heuristic, not a guarantee — flagged in ADR 0003 as one to watch
against real postings.
"""

from __future__ import annotations

import re
from functools import cache

from .models import Requirement, RequirementKind, RequirementSet
from .term_list import load_requirement_terms

# The vocabulary itself lives in data/requirement_terms.yaml (spec 002 AC-001), not here.
# Adding a term is a YAML edit and a `version` bump — no Python change, which is the point:
# whoever hits a missed requirement can fix it without touching the extractor. These module
# constants stay so the rest of the codebase keeps the same names to import.
_TERMS = load_requirement_terms()

SKILL_TERMS: dict[str, list[str]] = _TERMS.as_mapping("skills")
SENIORITY_TERMS: dict[str, list[str]] = _TERMS.as_mapping("seniority")
LANGUAGE_TERMS: dict[str, list[str]] = _TERMS.as_mapping("languages")
WORK_MODEL_TERMS: dict[str, list[str]] = _TERMS.as_mapping("work_models")

_REQUIRED_SECTION_MARKERS = tuple(_TERMS.section_markers.required)
_PREFERRED_SECTION_MARKERS = tuple(_TERMS.section_markers.preferred)


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
