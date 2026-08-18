"""Criterion 21: European Portuguese (PT-PT) is a distinct target from Brazilian Portuguese.
A deterministic, versioned, data-driven `brasileirismos` checker flags BR-only lexis/grammar
before the CV is accepted, reporting the offending line and its PT-PT replacement, and blocking
acceptance until resolved. See ADR 0004 decision 6 for the data-format and matching-approach
rationale.

Pure function over text — no LLM, no network — deliberately written before any generation/LLM
code exists (the spec's own note: it "needs no model to test").
"""

from __future__ import annotations

import re
from functools import cache
from pathlib import Path

import yaml
from pydantic import BaseModel, Field

from cv_writer.ingestion.requirements import word_boundary_pattern

DEFAULT_TERMS_PATH = Path(__file__).parent / "data" / "pt_pt_terms.yaml"


class PtPtTermEntry(BaseModel):
    """One brasileirismo entry: a term/pattern to flag and its PT-PT replacement."""

    id: str = Field(min_length=1)
    category: str = Field(min_length=1)
    pattern: str = Field(min_length=1)
    is_regex: bool = False
    replacement: str = Field(min_length=1)
    note: str | None = None


class PtPtTermList(BaseModel):
    """The whole versioned term list — see data/pt_pt_terms.yaml's own header comment for
    what "versioned, extendable without touching code" means concretely."""

    version: int
    entries: list[PtPtTermEntry]


class PtPtViolation(BaseModel):
    """One brasileirismo found in generated CV text, naming the offending line and its
    PT-PT replacement (criterion 21's exact wording)."""

    line_number: int = Field(ge=1)
    line_text: str
    term_id: str
    matched_text: str
    replacement: str


def load_pt_pt_terms(path: Path = DEFAULT_TERMS_PATH) -> PtPtTermList:
    """Load and validate a term list from YAML. `path` is parametrized so tests can point at
    an alternate fixture list without touching the shipped data file."""
    raw_text = Path(path).read_text(encoding="utf-8")
    data = yaml.safe_load(raw_text)
    return PtPtTermList.model_validate(data)


def check_pt_pt(markdown_text: str, terms: PtPtTermList | None = None) -> list[PtPtViolation]:
    """Scan `markdown_text` line by line for brasileirismos. Empty list = clean (accept);
    any violation blocks acceptance until resolved (criterion 21)."""
    if terms is None:
        terms = load_pt_pt_terms()

    violations: list[PtPtViolation] = []
    for line_number, line_text in enumerate(markdown_text.splitlines(), start=1):
        for entry in terms.entries:
            match = _match_entry(entry, line_text)
            if match is not None:
                violations.append(
                    PtPtViolation(
                        line_number=line_number,
                        line_text=line_text,
                        term_id=entry.id,
                        matched_text=match.group(0),
                        replacement=entry.replacement,
                    )
                )
    return violations


def _match_entry(entry: PtPtTermEntry, line_text: str) -> re.Match[str] | None:
    if entry.is_regex:
        return _compiled_regex(entry.pattern).search(line_text)
    return word_boundary_pattern(entry.pattern).search(line_text)


@cache
def _compiled_regex(pattern: str) -> re.Pattern[str]:
    # Mirrors word_boundary_pattern()'s own @cache (ingestion/requirements.py) — patterns
    # never change at runtime, and check_pt_pt() calls this once per (line x regex-entry), so
    # an uncached re.compile() would re-parse the same pattern string on every line of every
    # generation attempt. A code-review pass flagged the earlier uncached version.
    return re.compile(pattern, re.IGNORECASE)
