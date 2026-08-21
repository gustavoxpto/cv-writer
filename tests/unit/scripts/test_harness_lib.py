"""The markdown parsers the sensors are built on.

If these are wrong, every gate downstream is wrong in the same direction — silently passing
things it should catch. That is the failure mode worth testing hardest.
"""

from __future__ import annotations

import harness_lib as lib

SPEC = """# Spec: example

- **ID:** 099-example
- **Status:** signed-off
- **Size:** medium
- **Date:** 2026-08-20

## Why

Because the old behaviour produced one requirement from a real posting instead of twelve.

## Acceptance criteria

- **AC-001** — The system SHALL read terms from a dictionary file.
- **AC-002** — WHEN the posting is in Portuguese, the system SHALL match Portuguese terms.

## Out of scope

Anything to do with the web UI.

## Open questions

- [x] **OQ-1** (blocking) — resolved: pt-PT, not pt-BR.
- [ ] **OQ-2** (non-blocking) — whether to ship a Spanish dictionary too.

## Sign-off

- [x] Human has read this.
- [x] Criteria are testable.
"""


def test_parse_spec_reads_status_size_and_criteria():
    spec = lib.parse_spec(SPEC)
    assert spec.status == "signed-off"
    assert spec.size == "medium"
    assert spec.criterion_ids == ["AC-001", "AC-002"]
    assert "SHALL" in spec.criteria[0].text


def test_spec_is_signed_off_only_when_status_and_every_box_agree():
    assert lib.parse_spec(SPEC).signed_off is True
    unticked = SPEC.replace("- [x] Criteria are testable.", "- [ ] Criteria are testable.")
    assert lib.parse_spec(unticked).signed_off is False
    draft = SPEC.replace("**Status:** signed-off", "**Status:** draft")
    assert lib.parse_spec(draft).signed_off is False


def test_resolved_blocking_questions_do_not_count_as_open():
    spec = lib.parse_spec(SPEC)
    assert spec.blocking_open_questions == []

    reopened = SPEC.replace("- [x] **OQ-1** (blocking)", "- [ ] **OQ-1** (blocking)")
    assert len(lib.parse_spec(reopened).blocking_open_questions) == 1


def test_placeholders_are_found_but_real_comparisons_are_not():
    assert lib.find_placeholders("<feature name>")
    assert lib.find_placeholders("TODO: decide")
    assert lib.find_placeholders("the system SHALL …")
    # A "<" followed by a digit is a comparison, not a template hole.
    assert lib.find_placeholders("the system SHALL respond in < 200ms") == []


def test_an_ellipsis_is_unfinished_in_a_criterion_but_normal_in_prose():
    quotation = 'spec 001 asked "does extraction… graduate to an LLM step?"'
    assert lib.find_placeholders(quotation)
    assert lib.find_placeholders(quotation, prose=True) == []
    # An actually-unfilled hole is still caught in prose.
    assert lib.find_placeholders("<describe the problem>", prose=True)
    assert lib.find_placeholders("TBD", prose=True)


def test_a_criterion_wrapped_over_several_lines_keeps_its_whole_text():
    wrapped = SPEC.replace(
        "- **AC-001** — The system SHALL read terms from a dictionary file.",
        "- **AC-001** — WHEN a posting contains a Spanish requirement marker,\n"
        "  the system SHALL recognize that section as preferred.",
    )
    criterion = lib.parse_spec(wrapped).criteria[0]
    assert "SHALL" in criterion.text, "a wrapped criterion must not lose its SHALL"
    assert "preferred" in criterion.text


def test_template_instructions_in_html_comments_do_not_count_as_placeholders():
    text = "<!-- fill in <this> -->\nReal content with no holes."
    assert lib.find_placeholders(lib.strip_html_comments(text)) == []


TASKS = """# Tasks: 099-example

## Phase 1 — dictionary

- [x] **T-001** — load terms from YAML
  - **Covers:** AC-001
  - **Files:** `src/a.py`, `tests/unit/test_a.py`
  - **Gate:** quick
  - **Done when:** the loader returns every term in the file

- [ ] **T-002** — match Portuguese terms
  - **Covers:** AC-002
  - **Files:** `src/b.py`
  - **Gate:** full
  - **Done when:** a pt-PT posting yields more than one requirement

## Coverage matrix

| Criterion | Task(s) | Test level |
|---|---|---|
| AC-001 | T-001 | unit |
| AC-002 | T-002 | integration |
"""


def test_parse_tasks_reads_every_field_including_completion():
    tasks = lib.parse_tasks(TASKS)
    assert [t.id for t in tasks.tasks] == ["T-001", "T-002"]
    first, second = tasks.tasks
    assert first.done is True
    assert second.done is False
    assert first.covers == ["AC-001"]
    assert first.files == ["src/a.py", "tests/unit/test_a.py"]
    assert second.gate == "full"
    assert "more than one requirement" in second.done_when


def test_coverage_matrix_ids_are_parsed_separately_from_task_covers():
    tasks = lib.parse_tasks(TASKS)
    assert tasks.coverage_matrix_ids == ["AC-001", "AC-002"]
    # The matrix must not leak into any individual task's Covers field.
    assert all(len(task.covers) == 1 for task in tasks.tasks)


CONTRACT = """# Contract: 099-example

## Signature

- [x] Verifier has checked this list against `spec.md`.

## What will be built

- [x] **C-001** — a YAML-backed term dictionary
  - **Verifies:** AC-001
  - **Check:** `tests/unit/test_a.py` asserts every term in the fixture is returned

- [ ] **C-002** — Portuguese matching
  - **Verifies:** AC-002
  - **Check:** run the Lidl fixture and assert more than one requirement
"""


def test_parse_contract_reads_signature_and_items():
    contract = lib.parse_contract(CONTRACT)
    assert contract.signed is True
    assert [i.id for i in contract.items] == ["C-001", "C-002"]
    assert contract.items[0].verifies == ["AC-001"]
    assert contract.items[0].done is True
    assert contract.items[1].done is False


def test_contract_is_unsigned_while_the_box_is_empty():
    unsigned = CONTRACT.replace("- [x] Verifier has checked", "- [ ] Verifier has checked")
    assert lib.parse_contract(unsigned).signed is False


VALIDATION = """# Validation: 099-example

- **Verdict:** PASS
- **Date:** 2026-08-20

## Score

| Check | Score | Minimum to pass | Result |
|---|---|---|---|
| Criterion coverage | 2/2 | 100% of criteria | PASS |
| Discrimination sensor | 3/3 killed | 100% of mutations killed | PASS |

## Criterion evidence

| Criterion | Contract item | Evidence (`file:line`) | Matches spec outcome |
|---|---|---|---|
| AC-001 | C-001 | `tests/unit/test_a.py:12` | yes |
| AC-002 | C-002 | `tests/integration/test_b.py:44` | yes |
"""


def test_parse_validation_reads_verdict_scores_and_evidence():
    validation = lib.parse_validation(VALIDATION)
    assert validation.verdict == "PASS"
    assert len(validation.score_rows) == 2
    assert validation.evidence == {
        "AC-001": "tests/unit/test_a.py:12",
        "AC-002": "tests/integration/test_b.py:44",
    }


def test_evidence_without_a_line_number_is_not_evidence():
    vague = VALIDATION.replace("`tests/unit/test_a.py:12`", "covered in the unit tests")
    assert "AC-001" not in lib.parse_validation(vague).evidence


def test_current_feature_reads_the_live_state_file():
    feature, phase = lib.current_feature()
    assert isinstance(feature, str)
    assert isinstance(phase, str)


def test_bypass_is_detected_from_a_command_string():
    assert lib.bypass_requested("HARNESS_BYPASS=1 git commit -m x") is True
    assert lib.bypass_requested("git commit -m x") is False
