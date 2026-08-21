"""The validators must reject the shapes an agent actually produces under pressure.

Each test here is a fault injected on purpose: a criterion with no SHALL, a task tracing to
nothing, a contract item with no way to check it, a validation report claiming PASS on a failed
row. A validator that passes these is decoration, not a sensor.
"""

from __future__ import annotations

import check_commit
import validate_contract
import validate_spec
import validate_state
import validate_tasks
from test_harness_lib import CONTRACT, SPEC, TASKS, VALIDATION

# ---------------------------------------------------------------------------- validate_spec


def test_a_well_formed_spec_passes():
    assert validate_spec.check(SPEC).ok


def test_a_criterion_without_shall_is_rejected():
    loose = SPEC.replace(
        "- **AC-001** — The system SHALL read terms from a dictionary file.",
        "- **AC-001** — Terms come from a dictionary file, roughly.",
    )
    report = validate_spec.check(loose)
    assert not report.ok
    assert any("SHALL" in error for error in report.errors)


def test_a_criterion_still_holding_template_text_is_rejected():
    unfinished = SPEC.replace("read terms from a dictionary file", "do <the thing>")
    report = validate_spec.check(unfinished)
    assert not report.ok
    assert any("placeholder" in error for error in report.errors)


def test_duplicate_criterion_ids_are_rejected():
    duplicated = SPEC.replace("**AC-002**", "**AC-001**")
    report = validate_spec.check(duplicated)
    assert not report.ok
    assert any("more than once" in error for error in report.errors)


def test_claiming_sign_off_with_an_unticked_box_is_rejected():
    dishonest = SPEC.replace("- [x] Criteria are testable.", "- [ ] Criteria are testable.")
    report = validate_spec.check(dishonest)
    assert not report.ok
    assert any("unticked" in error for error in report.errors)


def test_claiming_sign_off_with_a_blocking_question_open_is_rejected():
    premature = SPEC.replace("- [x] **OQ-1** (blocking)", "- [ ] **OQ-1** (blocking)")
    report = validate_spec.check(premature)
    assert not report.ok
    assert any("blocking open question" in error for error in report.errors)


def test_a_missing_required_section_is_rejected():
    truncated = SPEC.replace("## Out of scope", "## Something else")
    report = validate_spec.check(truncated)
    assert not report.ok
    assert any("Out of scope" in error for error in report.errors)


def test_an_empty_why_is_rejected_because_nothing_justifies_the_work():
    hollow = SPEC.replace(
        "Because the old behaviour produced one requirement from a real posting instead of twelve.",
        "TBD",
    )
    assert not validate_spec.check(hollow).ok


# --------------------------------------------------------------------------- validate_tasks


def test_a_well_formed_task_list_passes_against_its_spec():
    assert validate_tasks.check(TASKS, spec_text=SPEC).ok


def test_a_task_tracing_to_no_criterion_is_rejected():
    untraced = TASKS.replace("  - **Covers:** AC-001\n", "")
    report = validate_tasks.check(untraced, spec_text=SPEC)
    assert not report.ok
    assert any("Covers" in error for error in report.errors)


def test_a_criterion_no_task_covers_is_rejected():
    partial = TASKS.replace("  - **Covers:** AC-002\n", "  - **Covers:** AC-001\n")
    report = validate_tasks.check(partial, spec_text=SPEC)
    assert not report.ok
    assert any("AC-002" in error and "no task covers it" in error for error in report.errors)


def test_a_task_claiming_a_criterion_that_does_not_exist_is_rejected():
    invented = TASKS.replace("  - **Covers:** AC-002\n", "  - **Covers:** AC-099\n")
    report = validate_tasks.check(invented, spec_text=SPEC)
    assert not report.ok
    assert any("AC-099" in error for error in report.errors)


def test_an_unknown_gate_level_is_rejected():
    sloppy = TASKS.replace("  - **Gate:** quick\n", "  - **Gate:** probably fine\n")
    report = validate_tasks.check(sloppy, spec_text=SPEC)
    assert not report.ok
    assert any("Gate" in error for error in report.errors)


def test_a_task_with_no_done_when_is_rejected():
    vague = TASKS.replace("  - **Done when:** the loader returns every term in the file\n", "")
    report = validate_tasks.check(vague, spec_text=SPEC)
    assert not report.ok
    assert any("Done when" in error for error in report.errors)


# ------------------------------------------------------------------------ validate_contract


def test_a_well_formed_contract_passes_against_its_spec():
    assert validate_contract.check(CONTRACT, spec_text=SPEC).ok


def test_a_contract_item_with_no_check_is_rejected():
    uncheckable = CONTRACT.replace(
        "  - **Check:** `tests/unit/test_a.py` asserts every term in the fixture is returned\n", ""
    )
    report = validate_contract.check(uncheckable, spec_text=SPEC)
    assert not report.ok
    assert any("Check" in error for error in report.errors)


def test_a_criterion_no_contract_item_promises_is_rejected():
    incomplete = CONTRACT.replace("  - **Verifies:** AC-002\n", "  - **Verifies:** AC-001\n")
    report = validate_contract.check(incomplete, spec_text=SPEC)
    assert not report.ok
    assert any("AC-002" in error for error in report.errors)


def test_an_unsigned_contract_warns_but_does_not_fail_while_it_is_being_drafted():
    draft = CONTRACT.replace("- [x] Verifier has checked", "- [ ] Verifier has checked")
    report = validate_contract.check(draft, spec_text=SPEC)
    assert report.ok
    assert any("not signed" in warning for warning in report.warnings)


# --------------------------------------------------------------------------- validate_state


def test_a_complete_validation_report_passes():
    assert validate_state.check(VALIDATION, spec_text=SPEC, contract_text=_all_done(CONTRACT)).ok


def _all_done(contract: str) -> str:
    return contract.replace("- [ ] **C-002**", "- [x] **C-002**")


def test_a_fail_verdict_is_not_a_finished_feature():
    failing = VALIDATION.replace("**Verdict:** PASS", "**Verdict:** FAIL")
    assert not validate_state.check(failing).ok


def test_a_criterion_with_no_file_line_evidence_is_rejected():
    handwaving = VALIDATION.replace("`tests/unit/test_a.py:12`", "covered by the unit tests")
    report = validate_state.check(handwaving, spec_text=SPEC)
    assert not report.ok
    assert any("AC-001" in error and "evidence" in error for error in report.errors)


def test_claiming_pass_while_a_score_row_failed_is_rejected():
    contradictory = VALIDATION.replace(
        "| Discrimination sensor | 3/3 killed | 100% of mutations killed | PASS |",
        "| Discrimination sensor | 1/3 killed | 100% of mutations killed | FAIL |",
    )
    report = validate_state.check(contradictory)
    assert not report.ok
    assert any("Discrimination sensor" in error for error in report.errors)


def test_a_score_row_that_was_never_run_is_rejected():
    unrun = VALIDATION.replace(
        "| Criterion coverage | 2/2 | 100% of criteria | PASS |",
        "| Criterion coverage | 0/0 | 100% of criteria | — |",
    )
    report = validate_state.check(unrun)
    assert not report.ok
    assert any("never actually run" in error for error in report.errors)


def test_a_report_still_full_of_template_text_is_not_evidence():
    unfinished = VALIDATION.replace("| yes |", "| <fill in> |")
    assert not validate_state.check(unfinished).ok


def test_validating_against_an_unsigned_spec_is_rejected():
    report = validate_state.check(VALIDATION, spec_text=SPEC.replace("signed-off", "draft"))
    assert not report.ok
    assert any("not signed off" in error for error in report.errors)


def test_unticked_contract_items_mean_the_feature_is_not_done():
    report = validate_state.check(VALIDATION, contract_text=CONTRACT)
    assert not report.ok
    assert any("C-002" in error for error in report.errors)


# ----------------------------------------------------------------------------- check_commit


def test_a_conventional_commit_passes():
    assert check_commit.check("feat(002): add pt-PT skill terms").ok


def test_a_scopeless_conventional_commit_passes():
    assert check_commit.check("docs: explain the discrimination sensor").ok


def test_a_prose_commit_message_is_rejected():
    assert not check_commit.check("Added some stuff.").ok


def test_an_unknown_type_is_rejected():
    assert not check_commit.check("wip(002): halfway there").ok


def test_a_capitalised_or_full_stopped_description_is_rejected():
    assert not check_commit.check("feat(002): Add terms").ok
    assert not check_commit.check("feat(002): add terms.").ok


def test_a_missing_blank_line_before_the_body_is_rejected():
    assert not check_commit.check("feat(002): add terms\nthe body starts immediately").ok


def test_a_breaking_change_marker_without_a_footer_is_rejected():
    assert not check_commit.check("feat(002)!: drop the old dictionary format").ok
    assert check_commit.check(
        "feat(002)!: drop the old dictionary format\n\nBREAKING CHANGE: term files must be YAML"
    ).ok
