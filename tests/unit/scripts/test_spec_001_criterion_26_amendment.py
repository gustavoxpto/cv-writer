"""AC-005 / contract C-008: spec 001's criterion 26 is amended, never deleted (hard rule #1),
so that "standard section headings (Experience, Education, Skills)" no longer reads as a
mandate for the literal English words regardless of output language -- spec 003's whole reason
for existing. The amendment must be recorded, not silent: a dated entry in spec 001's own
Revision log, following the 2026-08-17 entry's form.

Whitespace-normalization on the phrase check is load-bearing, not tidiness (`.specs/LESSONS.md`
L-007): "standard section headings (Experience, Education, Skills)" is line-wrapped in the
source today (it breaks after "Education," and resumes indented on the next line), so a naive
contiguous-substring check against the raw text is already green before any amendment and would
prove nothing. This test collapses runs of whitespace to a single space before comparing, so it
actually has to observe the phrase gone, not merely un-joined by a line break.
"""

from __future__ import annotations

import re
from pathlib import Path

SPEC_001_PATH = Path(__file__).resolve().parents[3] / "specs" / "features" / "001-cv-writer.md"

_WHITESPACE_RUN = re.compile(r"\s+")


def _normalize_whitespace(text: str) -> str:
    return _WHITESPACE_RUN.sub(" ", text)


def _split_criteria_and_revision_log() -> tuple[str, str]:
    text = SPEC_001_PATH.read_text(encoding="utf-8")
    criteria_part, _, log_part = text.partition("### Revision log")
    return criteria_part, log_part


def test_the_scan_looked_at_a_real_non_empty_file():
    # A guard against this test silently passing because SPEC_001_PATH resolved to nothing or
    # an empty file (e.g. a path typo).
    assert SPEC_001_PATH.exists()
    criteria_part, log_part = _split_criteria_and_revision_log()
    assert len(criteria_part) > 100
    assert len(log_part) > 20


def test_criterion_26_no_longer_mandates_the_literal_english_heading_words():
    criteria_part, _log_part = _split_criteria_and_revision_log()

    normalized = _normalize_whitespace(criteria_part)

    assert "standard section headings (Experience, Education, Skills)" not in normalized


def test_criterion_26_still_exists_and_still_names_ats_safe_structure():
    # Amended, not deleted (hard rule #1): criterion 26 itself must still be present and must
    # still speak to ATS-safe structure -- only the parenthetical example changes meaning.
    criteria_part, _log_part = _split_criteria_and_revision_log()

    assert re.search(r"^26\. ", criteria_part, flags=re.MULTILINE) is not None
    assert "ATS-safe structure" in criteria_part


def test_revision_log_records_a_dated_entry_naming_spec_003_and_criterion_26():
    _criteria_part, log_part = _split_criteria_and_revision_log()

    entries = re.findall(
        r"^- \*\*(\d{4}-\d{2}-\d{2}).*$",
        log_part,
        flags=re.MULTILINE,
    )
    assert entries, "no dated Revision-log entries found at all"

    matching_entries = [
        match
        for match in re.finditer(r"^- \*\*(\d{4}-\d{2}-\d{2}).*$", log_part, flags=re.MULTILINE)
        if match.group(1) > "2026-08-17"
    ]
    assert matching_entries, "no Revision-log entry dated after 2026-08-17"

    # An entry's body can span multiple lines (see the 2026-08-17 entry itself), so pull the
    # text from the entry's own line up to (but not including) the next dated bullet, or the
    # end of the log if it's the last one.
    entry_starts = [match.start() for match in matching_entries]
    for start in entry_starts:
        next_bullet = re.search(r"\n- \*\*", log_part[start + 1 :])
        end = start + 1 + next_bullet.start() if next_bullet else len(log_part)
        body = log_part[start:end]
        if "criterion 26" in body.lower() and "003" in body:
            return

    raise AssertionError(
        "no post-2026-08-17 Revision-log entry mentions both 'criterion 26' and '003'"
    )
