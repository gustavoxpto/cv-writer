"""Spec 002 AC-001: the requirement vocabulary as versioned data rather than Python literals.

Same arrangement as `generation/pt_pt_checker.py`'s brasileirismos list, deliberately — one
pattern for "a curated list this tool matches against", not two. Extending the vocabulary is a
YAML edit plus a `version` bump; no code change, no test change beyond naming the addition.

Why this exists at all: the dictionaries this replaces were entirely English software-engineering
terms, so the first real Spanish posting extracted one requirement and generation then failed for
want of anything to match against — a quiet empty result rather than a loud failure
(`.specs/LESSONS.md` L-004). Vocabulary that lives in code gets extended by whoever is editing
code; vocabulary that lives in data gets extended by whoever hit the gap.
"""

from __future__ import annotations

from functools import cache
from pathlib import Path

import yaml
from pydantic import BaseModel, Field, model_validator

DEFAULT_TERMS_PATH = Path(__file__).parent / "data" / "requirement_terms.yaml"

TERM_GROUPS = ("skills", "seniority", "languages", "work_models")


class TermEntry(BaseModel):
    """One canonical value and the phrases that count as a match for it.

    `key` is what the rest of the system reasons about; `phrases` are what appears in a posting.
    Keys are chosen to textually match the profile's own skill names (see
    `matching/matcher.py::_skill_name_matches`), so a match here can actually meet evidence.
    """

    key: str = Field(min_length=1)
    phrases: list[str] = Field(min_length=1)


class SectionMarkers(BaseModel):
    """Headings that switch the extractor between the required and preferred zones of a posting.

    A heuristic, not a guarantee — see `requirements.py::_skill_zones` for how the zones are
    resolved and which ambiguity it has to handle.
    """

    required: list[str]
    preferred: list[str]


class RequirementTermList(BaseModel):
    """The whole versioned vocabulary — see `data/requirement_terms.yaml`'s own header for what
    "versioned, extendable without touching code" means concretely."""

    version: int
    skills: list[TermEntry]
    seniority: list[TermEntry]
    languages: list[TermEntry]
    work_models: list[TermEntry]
    section_markers: SectionMarkers

    @model_validator(mode="after")
    def _reject_duplicate_keys(self) -> RequirementTermList:
        """A YAML list gives up the one guarantee a Python dict had for free: unique keys. With a
        duplicate, the second entry silently wins and the first entry's phrases stop matching
        anything — vocabulary that looks present and is not, which is exactly L-004's failure
        shape. Fail at load, loudly, naming the key."""
        for group in TERM_GROUPS:
            seen: set[str] = set()
            for entry in getattr(self, group):
                if entry.key in seen:
                    raise ValueError(
                        f"duplicate canonical key {entry.key!r} in '{group}' — the later entry "
                        f"would silently replace the earlier one, and half the phrases would "
                        f"stop matching"
                    )
                seen.add(entry.key)
        return self

    def as_mapping(self, group: str) -> dict[str, list[str]]:
        """`{canonical key: phrases}` for one group, the shape the matching code consumes."""
        if group not in TERM_GROUPS:
            raise ValueError(f"unknown term group {group!r}; expected one of {TERM_GROUPS}")
        return {entry.key: list(entry.phrases) for entry in getattr(self, group)}


@cache
def load_requirement_terms(path: Path = DEFAULT_TERMS_PATH) -> RequirementTermList:
    """Load and validate the vocabulary from YAML. `path` is parametrized so tests can point at
    an alternate list without touching the shipped file, exactly as `load_pt_pt_terms` does.
    Cached because the file never changes at runtime and extraction is called per posting."""
    raw_text = Path(path).read_text(encoding="utf-8")
    data = yaml.safe_load(raw_text)
    return RequirementTermList.model_validate(data)
