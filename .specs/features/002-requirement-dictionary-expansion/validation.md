# Validation: 002-requirement-dictionary-expansion

- **Verdict:** PASS
- **Verdict detail:** all six criteria are covered with real evidence, both surviving mutants
  found across iterations 1 and 2 are now closed with tests that actually catch the fault they
  name, the overstated commit-message claim from iteration 2 is now backed by a real sensor, the
  full discrimination sweep for this iteration (2 new-mutation checks plus a 2-mutation regression
  re-run of iteration 2's set) killed cleanly, and `gate.py build` exits 0 with 391 tests passing.
- **Verifier:** `verifier` (fresh dispatch, did not write this code)
- **Date:** 2026-08-21
- **Commit range:** `2dd5146..32ed51f`
- **Iteration:** 3 of max 3

## History — iterations 1 and 2, so this is not read in isolation

**Iteration 1** (`73c2b60..09200df`, 2026-08-20) — FAIL. Two reasons: (a) AC-005/AC-005a had zero
coverage — the redacted fixture had never actually been committed, tracked as blocked-not-defective;
(b) a surviving mutant on `RequirementTermList.as_mapping`'s unknown-group `ValueError`
(`term_list.py:81-82`) — no test exercised the invalid-group branch, so replacing the `raise` with
a silent `return {}` left all 35 tests green.

**Resolved before iteration 2** by `a2b8faf` (`test_as_mapping_rejects_an_unknown_group`, closing
the mutant) and `3acb395` (committing the fixture and `test_real_posting.py`, closing AC-005 /
AC-005a).

**Iteration 2** (`a2b8faf..3acb395`, 2026-08-21) — FAIL. All six criteria now had evidence and the
gate was green, but a fresh discrimination sweep against the *new* T-005 code found a surviving
mutant: `test_real_posting.py::_posting_text()` strips `#`-prefixed provenance-header lines before
extraction, but nothing tested that stripping. Feeding the raw file — header included — into
`extract_requirements` left all six tests in the file green, and the AC-005a provenance-ratio
sensor actually read *better* with the mutation applied (unknown-word ratio 0.870 → 0.895) rather
than warning. Separately, commit `3acb395`'s message claimed redaction was "assert-checked as
applied and then assert-checked as absent" — no such assertion existed anywhere in the committed
repo.

**Resolved before this iteration** by `2dd5146` (`test_the_provenance_header_is_not_extracted_as_posting_text`, closing the header mutant, its docstring recording the 0.870→0.895 flattery
finding verbatim) and `32ed51f` (`test_the_fixture_carries_no_employer_identifying_detail` +
`test_the_fixture_shows_where_it_was_redacted`, turning the redaction claim into a standing
sensor). `3acb395`'s message was deliberately left unamended; `32ed51f`'s message states plainly
what was wrong with it.

This iteration is a full re-verification of both fixes, not a rubber stamp — each was mutated
independently in an isolated worktree and confirmed to fail before being accepted as closed.

## Score

| Check | Score | Minimum to pass | Result |
|---|---|---|---|
| Criterion coverage (all six) | 6/6 | 100% of criteria | PASS |
| Assertion depth | 6/6 non-shallow | 100% non-shallow | PASS |
| Contract completion | 6/6 ticked | 100% of contract items | PASS |
| Discrimination sensor | 6/6 killed | 100% of mutations killed | PASS |
| Gate (`gate.py build`) | exit 0, 391 passed | exit 0 | PASS |

## Criterion evidence

Unchanged in substance from iteration 2 for AC-001..004/006 (no code in those areas changed this
iteration); AC-005/AC-005a evidence extended with the two new sensors.

| Criterion | Contract item | Evidence (`file:line`) | Asserted value matches the spec's stated outcome |
|---|---|---|---|
| AC-001 | C-001 | `tests/unit/ingestion/test_term_list.py:161` `test_shipped_term_file_loads_and_validates`; `:169` `isinstance(terms.version, int)` and `terms.version >= 1`; `:244` `test_loader_accepts_an_alternate_path`; `:268` `test_requirements_module_holds_no_vocabulary_literals` | yes |
| AC-002 | C-002 | `tests/unit/ingestion/test_term_list.py:176` snapshot `==` for skills; `:182` Appendix A keys/phrases; `:196` snapshot `==` for seniority and work_models; `:218`/`:230` no-loss + `EXPECTED_*` equality split for languages/section_markers | yes — split re-confirmed equivalent strength again this iteration (see regression mutations below) |
| AC-003 | C-003 | `tests/unit/ingestion/test_requirement_sections.py:62,72,84,93` — required vs. preferred, both languages, both directions | yes |
| AC-004 | C-004 | `tests/unit/ingestion/test_term_list.py:347,358` — all 5 native names, value and `source_phrase` | yes |
| AC-005 | C-005 | `tests/integration/ingestion/test_real_posting.py:96` `test_the_real_posting_yields_more_than_one_requirement` — `assert len(extracted.requirements) > 1` and `>= 10`; `:104` named canonical values `<=` required; `:121` languages/seniority named values; fixture at `tests/integration/ingestion/fixtures/posting_es_redacted.txt` | yes — `>1` and `>=10` both asserted, pinning the actual before/after (1 requirement pre-feature, 11 now) |
| AC-005a | C-005 | `test_real_posting.py:39` `test_the_provenance_header_is_not_extracted_as_posting_text` (new, closes iteration 2's mutant — asserts the header is present in the raw file and absent, including no stray `#` lines, from the text actually fed to the extractor); `:132` `test_source_phrases_quote_the_posting_verbatim_with_accents`; `:169` `test_the_fixture_is_real_prose_and_not_written_from_the_term_file` (ratio > 0.8, real value 0.870); `:76` `test_the_fixture_carries_no_employer_identifying_detail` (new, closes the redaction-claim gap — asserts 9 named identifiers, including "Lidl", absent from the raw file); `:86` `test_the_fixture_shows_where_it_was_redacted` (new — asserts 5 placeholder markers are present, so absence-of-identity isn't indistinguishable from an empty file) | yes — provenance, verbatim-quoting, header-exclusion and redaction are now each independently sensor-checked, not merely inspected |
| AC-006 | C-006 | `tests/unit/ingestion/test_no_model_calls.py:118,139,195,219` — AST scan + socket-killed run + repeatability | yes |

## Assertion depth

- No tautologies. No criterion proved solely by "no exception raised."
- `test_the_provenance_header_is_not_extracted_as_posting_text` targets the actual output value
  (`stripped`), not just that `_posting_text()` runs: it asserts specific header content
  ("AC-005a", "PROVENANCE") is absent from the stripped text and present in the raw file, plus a
  length-decrease check and a per-line `#`-prefix check. Not a call-count or existence check.
- `test_the_fixture_carries_no_employer_identifying_detail` names 9 concrete strings (employer
  name in two cases, requisition number, street name, town, postal code, two salary figures) and
  checks each individually against the *whole raw file including the header* — closing exactly
  the gap iteration 2 found (the header itself was unchecked ground).
- `test_the_fixture_shows_where_it_was_redacted` is the necessary complement: without it, an
  empty or entirely-redacted-to-nothing fixture would also pass the identity-absence test. This
  is exactly the "absence alone proves nothing" discipline this mission's template asks for.
- Re-verified experimentally (not just read) that both new tests catch the fault they claim to —
  see Discrimination sensor below.

## Discrimination sensor

Ran in an isolated `git worktree` at
`C:/Users/Admin/AppData/Local/Temp/claude/C--g-projetos/0e353e3c-72d0-4fd0-8ff7-ec310ee37b4c/scratchpad/wt002c`, checked out at `32ed51f` (detached HEAD). Never used `git stash`, never touched the
real working tree. Per L-006, forced `PYTHONPATH` to the worktree's own `src/` ahead of the shared
venv's editable-install `.pth` target and verified before trusting any result:
`PYTHONPATH="C:/Users/Admin/AppData/Local/Temp/claude/C--g-projetos/0e353e3c-72d0-4fd0-8ff7-ec310ee37b4c/scratchpad/wt002c/src" C:/g/projetos/.venv/Scripts/python.exe -c "import cv_writer; print(cv_writer.__file__)"`
resolved to the worktree's own `src/cv_writer/__init__.py`. Baseline: 84 passed
(`tests/unit/ingestion` + `tests/integration/ingestion`) — up from iteration 2's 81, matching the
3 new tests.

**Two mutations targeting the fixes from this round:**

| # | Mutation | File | Test expected to fail | Killed? |
|---|---|---|---|---|
| 1 | Strip-the-stripping regression — `_posting_text()` returns the raw file unfiltered again, the exact fault iteration 2 found | `tests/integration/ingestion/test_real_posting.py:32` | `test_the_provenance_header_is_not_extracted_as_posting_text` | **yes** — 1 failed, 8 passed. Failed specifically on `assert "AC-005a" not in stripped` — the header text leaked through, caught immediately. |
| 2 | Redaction leak — replace `[EMPRESA]` with `Lidl` at `posting_es_redacted.txt:23`, simulating the employer name surviving a re-fetch | `tests/integration/ingestion/fixtures/posting_es_redacted.txt:23` | `test_the_fixture_carries_no_employer_identifying_detail` | **yes** — 1 failed, 8 passed. Failed on `assert identifier not in raw` for `identifier='Lidl'`, naming the exact leaked string. |

**Regression check — two of iteration 2's mutations re-run to confirm nothing broke in between:**

| # | Mutation | File | Tests expected to fail | Killed? | vs. iteration 2 |
|---|---|---|---|---|---|
| 3 | `_skill_zones` always returns the required zone (`return [(0, "required")]` before the real body) | `src/cv_writer/ingestion/requirements.py:60` | `test_requirement_sections.py`/`test_requirements.py` preferred-zone tests | **yes** — 4 failed, 80 passed | same 4 failures as iteration 2 — no regression |
| 4 | `RequirementTermList.as_mapping` drops the last phrase of every entry (`list(entry.phrases)[:-1]`) | `src/cv_writer/ingestion/term_list.py:83` | most of `test_term_list.py`, `test_requirement_sections.py`, `test_real_posting.py`, `test_no_model_calls.py`'s behavioural test | **yes** — 19 failed, 65 passed | same 19-failure spread as iteration 2 — no regression |

All 4 mutations run this iteration killed. Combined with iterations 1–2's already-closed mutants
(`as_mapping` unknown-group guard, `source_phrase` corruption, missing skill key), this feature
now has **zero surviving mutants across three verification passes**.

Reverted each mutation individually (`git checkout --`) and confirmed `git status --porcelain`
clean inside the worktree before the next. Final full re-run inside the worktree after all
reverts: 84 passed, 0 failed — back to baseline.

Scratch worktree removed with `git worktree remove` after the sensor run (created by me under the
session scratchpad for this run; explicit permission covers a worktree the verifier itself
created). Real repo `git status --porcelain` before this iteration's sensor work and after:

```
 M .specs/features/002-requirement-dictionary-expansion/validation.md
 M .specs/test-census.json
```

Identical before and after — the `validation.md` change is this report being written (the only
file this mission permits me to write), and `test-census.json` is the orchestrator's own
pre-existing, untouched state-tracking change.

## Contract walk

| Item | Status | Evidence |
|---|---|---|
| C-001 | ✅ ticked, confirmed | unchanged since iteration 2 |
| C-002 | ✅ ticked, confirmed | unchanged since iteration 2; split re-confirmed by regression mutations 3/4 this run |
| C-003 | ✅ ticked, confirmed | unchanged since iteration 2 |
| C-004 | ✅ ticked, confirmed | unchanged since iteration 2 |
| C-005 | ✅ ticked, confirmed, and now backed by two additional sensors this iteration | fixture committed; `test_real_posting.py` covers count, named values, provenance (now including header-exclusion), verbatim `source_phrase`, and redaction (now including presence-of-placeholder as the complement to absence-of-identity) |
| C-006 | ✅ ticked, confirmed | unchanged since iteration 2 |

All 6 contract items ticked and independently confirmed with real, executed evidence.

## Ranked gaps

None. Both gaps raised at the end of iteration 2 are closed and re-verified by independent
mutation in this iteration, not merely re-read:

- Gap 1 (surviving mutant on the provenance-header-stripping) — closed by `2dd5146`, confirmed
  killed by mutation 1 above.
- Gap 2 (overstated redaction claim in `3acb395`'s commit message) — closed by `32ed51f`,
  confirmed killed by mutation 2 above. `3acb395`'s message remains unamended by design, with the
  correction recorded honestly in `32ed51f` rather than by rewriting history.
- Gap 3 from iteration 2 (C-002's Check-text wording describing one uniform snapshot `==` where
  two of six groups are necessarily split) was accepted as a non-gap at the end of iteration 2 and
  carried forward unchanged here — no action taken, none needed. Re-confirmed equivalent strength
  by regression mutations 3/4.

## Lessons

No new line for `.specs/LESSONS.md` this iteration — the lesson this cycle produced ("a
discrimination sensor aimed only at `src/` misses gaps in test-file helper logic") was already
recorded as a candidate at the end of iteration 2 and is superseded by the fact that the actual
fix landed as a same-file test addition, which is the expected remedy, not a new generalizable
rule beyond what was already written down.
