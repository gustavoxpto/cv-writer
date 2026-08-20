# Validation: 002-requirement-dictionary-expansion

- **Verdict:** FAIL
- **Verdict detail:** blocked, not defective. AC-005/C-005 is a knowingly incomplete item, not
  a gap found by this validation; all five closable criteria pass on their own merits, but the
  feature as a whole cannot be PASS while a criterion has zero coverage.
- **Verifier:** `verifier` (fresh dispatch, did not write this code)
- **Date:** 2026-08-20
- **Commit range:** `73c2b60..09200df`
- **Iteration:** 1 of max 3

## Score

| Check | Score | Minimum to pass | Result |
|---|---|---|---|
| Criterion coverage (AC-001..004, 006) | 5/5 | 100% of closable criteria | PASS |
| Criterion coverage (all six, AC-005 included) | 5/6 | 100% of criteria | FAIL (AC-005 blocked, tracked, not a surprise) |
| Assertion depth | 5/5 non-shallow | 100% non-shallow | PASS |
| Contract completion | 5/6 ticked, 1 open (C-005, blocked) | 100% of contract items | FAIL on raw count, matches the scope note |
| Discrimination sensor | 4/5 killed | 100% of mutations killed | FAIL — 1 surviving mutant |
| Gate (`gate.py build`) | exit 0, 381 passed | exit 0 | PASS |

The scope note for this run says AC-005/C-005 is knowingly incomplete and not to be hunted as a
defect. I have not treated it as a defect. It is still a criterion with zero test evidence, so
the table above records it honestly rather than silently dropping it from the denominator — that
is a decision for the human (ship the four-fifths-done feature as a tracked partial, or hold the
merge), not mine to make by omission. The one genuine gap this validation found is independent of
AC-005: the surviving mutant on `term_list.as_mapping`'s unknown-group branch (see Discrimination
sensor below).

## Criterion evidence

| Criterion | Contract item | Evidence (`file:line`) | Asserted value matches the spec's stated outcome |
|---|---|---|---|
| AC-001 | C-001 | `tests/unit/ingestion/test_term_list.py:161` `assert DEFAULT_TERMS_PATH.exists()` / `.suffix == ".yaml"` / `isinstance(terms, RequirementTermList)`; `:169` `isinstance(terms.version, int)` and `terms.version >= 1`; `:244` `test_loader_accepts_an_alternate_path` builds an alternate YAML and asserts `loaded.version == 7` and `loaded.as_mapping("skills") == {"basket weaving": ["basket weaving"]}`; `:268` `test_requirements_module_holds_no_vocabulary_literals` asserts 6 sample literals (`"python"`, `"kubernetes"`, `"se valorará"`, `"visa sponsorship"`, `"engineering manager"`, `"consultoría estratégica"`) are absent from `requirements.py`'s source text | yes — "versioned YAML data file, in the same shape as pt_pt_terms.yaml, rather than a hardcoded Python dictionary" is directly asserted: file exists, is YAML, has an int version, loads through a validating loader, and the consuming module carries no literal vocabulary |
| AC-002 | C-002 | `tests/unit/ingestion/test_term_list.py:176` `assert terms.as_mapping("skills") == SNAPSHOT_387D937_SKILLS` (34-key `==`, not subset); `:182` `test_appendix_a_terms_are_present_with_their_exact_phrases` asserts each of the 8 Appendix A keys individually plus 4 specific accented phrases; `:196` `assert terms.as_mapping("seniority") == SNAPSHOT_387D937_SENIORITY` and `and work_models == SNAPSHOT_387D937_WORK_MODELS`; `:218` and `:230` (see note below) | yes for skills/seniority/work_models (exact `==` against the frozen 387d937 snapshot, matching the contract's explicit "not a subset check" instruction). **Languages and section markers are asserted differently — see the note below; I judge this preserves, not weakens, the required strength, but it is a deliberate deviation from the contract's literal wording worth flagging.** |
| AC-003 | C-003 | `tests/unit/ingestion/test_requirement_sections.py:62` `assert "project planning" in required` + `"microsoft office" in required` (Spanish `Requisitos:`); `:72` `assert "strategic consulting" in preferred` + `"google workspace" in preferred` **and** `not in required` (Spanish `Se valorará:`); `:84` same pair for Portuguese `Requisitos:`; `:93` same not-also-required pair for Portuguese `Diferenciais:` | yes — required vs. preferred is asserted both ways (in the right zone, and explicitly not leaking into the other), for both languages named in AC-003 |
| AC-004 | C-004 | `tests/unit/ingestion/test_term_list.py:335` `test_native_language_names_resolve_to_the_canonical_language` — for each of the 5 native names in `NATIVE_LANGUAGE_NAMES` (`inglés→english`, `español→spanish`, `alemán→german`, `português→portuguese`, `français→french`), `assert canonical in languages`; `:346` `test_native_language_names_keep_their_own_spelling_as_the_source_phrase` asserts `matched[0].source_phrase == native` (accented spelling preserved, not the canonical key) | yes — covers all 5 names AC-004 names by cross-reference to Appendix A.2, plus the `source_phrase` fidelity the spec's own criterion 12 promise implies |
| AC-005 | C-005 | none — `tests/integration/ingestion/test_real_posting.py` and the fixture do not exist | **no evidence — blocked by design, per this run's explicit scope, not a defect found here** |
| AC-006 | C-006 | `tests/unit/ingestion/test_no_model_calls.py:118` `test_deterministic_module_imports_no_model_client`, parametrized over every `.py` in `ingestion/` and `matching/`, `assert offenders == []`; self-test `test_the_scan_itself_catches_a_planted_model_import` (same file) proves the AST scan actually fires on all three import shapes (plain, from-import, dynamic); `:195` `test_extract_and_score_complete_with_the_network_unavailable` patches `socket.socket`/`socket.create_connection` to raise, then asserts real extracted values (`"project planning" in values`, `"english" in {r.value for r in result.of_kind(RequirementKind.LANGUAGE)}`) and `len(report.matches) == len(requirement_set.requirements)`, not just "did not raise"; `:219` `test_scoring_is_repeatable` asserts two independent extractions produce identical `.score`, `.value` ordering, and `.status` ordering | yes — structural (AST) and behavioural (network-killed) checks are both present, and the behavioural check asserts real values, not merely "no exception" |

### Note on AC-002's languages/section-markers assertion shape

The contract (C-002's Check) specifies "a frozen literal snapshot [and] asserts the loaded file
equals it exactly (`==`, not a subset check)" for "the four pre-migration dictionaries and the
two marker tuples" as one undifferentiated group. The implementation applies `==` against the
frozen snapshot for `skills`, `seniority`, and `work_models` (three of the four dictionaries,
untouched by this feature), but for `languages` and `section_markers` (the two groups this
feature actually extends) it instead asserts (a) every snapshot entry is still present
(no-loss, `tests/unit/ingestion/test_term_list.py:218-228` and `:230-241`) and (b) the *current*
content equals a locally-defined `EXPECTED_LANGUAGES` / `EXPECTED_REQUIRED_MARKERS` /
`EXPECTED_PREFERRED_MARKERS` constant that is the snapshot plus the specific AC-003/AC-004
additions, stated in full in the test file (`:207-214`).

I ran the discrimination sensor against this exact split (mutations 1–3 below) and it kills
cleanly in both directions: dropping a pre-existing marker/phrase fails the no-loss half, and
dropping a spec-002 addition fails the equality-to-`EXPECTED_*` half. So behaviourally this is
**not weaker** than a single frozen `==` would have been — it is functionally equivalent
strength, split across two assertions because a single static literal (the `387d937` snapshot)
cannot describe a dictionary this same feature is required to change. I judge this satisfies
C-002's intent even though it does not literally match the Check's "one snapshot, one `==`"
description for all four dictionaries. Flagging it rather than passing silently, per this
mission's instruction, because the contract's Check text was written before the implementer hit
the problem that a snapshot-of-everything can't also be a snapshot-of-the-unchanged-parts.

## Assertion depth

All five closable criteria clear the bar in `.specs/templates/validation.md`:

- No tautologies found.
- No criterion is proved solely by "no exception raised" — AC-006's socket-killed test asserts
  specific extracted values and a specific `len(report.matches)` equality, not just completion.
- No call-count-only assertions.
- `tests/requirement_sections.py`'s ordering trick (PREFERRED heading placed *above* REQUIRED in
  both fixtures) was checked directly: I re-read `_skill_zones`/`_zone_at` in
  `src/cv_writer/ingestion/requirements.py:63-108`. Zone resolution is "last boundary at or
  before this offset, defaulting to required." With "required" as the default, a fixture that put
  the required heading first would pass even if "requisitos" were entirely absent from the
  marker list — the skill would already be in the default required zone. Putting "Se valorará"
  first forces a return-to-required transition that can only happen if "requisitos" is actually
  recognised. I confirmed this experimentally: mutation 1 (removing "requisitos" from the term
  file) flips exactly the two tests that rely on this ordering
  (`test_spanish_requisitos_heading_marks_skills_as_required`,
  `test_portuguese_requisitos_heading_marks_skills_as_required`) from pass to fail. The reasoning
  holds and no assertion in that file would have passed unchanged against pre-feature code
  (pre-feature, `SPANISH_POSTING`/`PORTUGUESE_POSTING` would have had zero Spanish/Portuguese
  markers, so everything in both fixtures would have been "required" and the four
  preferred-only assertions would already fail against today's file, let alone pre-feature).
- `test_term_list.py`'s no-loss + equality split for languages/section-markers (discussed above)
  was checked for whether it quietly weakened C-002. It did not, on the discrimination evidence:
  mutations 1 and 2 below independently fail both halves of the split. It is a legitimate
  response to a real conflict in the contract's Check text (see note above), not a weakening.

## Discrimination sensor

Ran in an isolated `git worktree` at
`C:/Users/Admin/AppData/Local/Temp/claude/C--g-projetos/0e353e3c-72d0-4fd0-8ff7-ec310ee37b4c/scratchpad/wt002`,
checked out at `09200df` (detached HEAD). Never used `git stash`; never touched the real working
tree. **One methodological note that matters for anyone repeating this**: the shared `.venv` at
`C:/g/projetos/.venv` holds an *editable* install whose `.pth` file points at
`C:/g/projetos/src/cv_writer`, not the worktree copy — running pytest from inside the worktree
using that interpreter silently tests the real repo's unmutated code (confirmed: mutation 1 first
"passed" 35/35 until this was caught). Fixed by setting `PYTHONPATH` to the worktree copy's `src/` directory ahead of the
editable install path for every mutation run below; each result was then verified to trace back
to the worktree's own mutated file via `git status --porcelain` inside the worktree before/after.

| # | Mutation | File | Tests expected to fail | Killed? |
|---|---|---|---|---|
| 1 | Remove `"requisitos"` from `section_markers.required` | `src/cv_writer/ingestion/data/requirement_terms.yaml:274` | `tests/unit/ingestion/test_requirement_sections.py::test_spanish_requisitos_heading_marks_skills_as_required`, `::test_portuguese_requisitos_heading_marks_skills_as_required`, `tests/unit/ingestion/test_term_list.py::test_section_markers_extend_the_snapshot_without_losing_any` | **yes** — 3 failed, 32 passed |
| 2 | Remove `"português"` from the `portuguese` language entry's phrases | `src/cv_writer/ingestion/data/requirement_terms.yaml:216` | `tests/unit/ingestion/test_term_list.py::test_language_terms_extend_the_snapshot_without_losing_any`, `::test_native_language_names_resolve_to_the_canonical_language`, `::test_native_language_names_keep_their_own_spelling_as_the_source_phrase` | **yes** — 3 failed, 32 passed |
| 3 | Drop the Appendix A `strategic consulting` skill key entirely | `src/cv_writer/ingestion/data/requirement_terms.yaml:149-151` | `tests/unit/ingestion/test_requirement_sections.py::test_spanish_se_valorara_heading_marks_skills_as_preferred_only`, `::test_portuguese_diferenciais_heading_marks_skills_as_preferred_only`, `::test_a_posting_with_no_recognised_heading_still_defaults_to_required`, `tests/unit/ingestion/test_term_list.py::test_skill_terms_match_the_387d937_snapshot_exactly`, `::test_appendix_a_terms_are_present_with_their_exact_phrases` | **yes** — 5 failed, 30 passed |
| 4 | `RequirementTermList.as_mapping` silently returns `{}` for an unknown group instead of raising `ValueError` | `src/cv_writer/ingestion/term_list.py:81-82` | *(none — no test calls `as_mapping` with an invalid group name)* | **SURVIVED** — 35/35 still passed |
| 5 | Neuter the duplicate-key `model_validator` (`if False and entry.key in seen:`) so it never raises | `src/cv_writer/ingestion/term_list.py:70` | `tests/unit/ingestion/test_term_list.py::test_duplicate_canonical_keys_are_rejected` | **yes** — 1 failed, 34 passed |

4 of 5 mutations killed. Mutation 4 is a genuine surviving mutant: the "unknown group" branch of
`as_mapping` (`term_list.py:81-82`) is unreachable by every test in the suite. Nothing in the spec
or contract names this branch directly (`C-001`'s Check does not mention it), so it is not itself
an AC gap — but it is dead-code-from-a-testing-perspective defensive logic that could be deleted,
inverted, or broken without any sensor noticing, in a module whose whole stated purpose (per its
own docstring) is to fail loudly rather than silently on bad input. Worth a follow-up test
(`pytest.raises(ValueError, match="unknown term group")` against `as_mapping("nonexistent")`),
not severe enough on its own to block this feature given it maps to no numbered criterion.

After the sensor run, working tree confirmed unchanged:
```
$ git status --porcelain   # real repo, before and after
 M .specs/STATE.md
 M .specs/test-census.json
```
Identical before and after (both are the orchestrator's own STATE-phase and test-census updates
from before this validation began, untouched by anything I did). The worktree itself
(the scratchpad worktree) still exists — I did not run `git worktree remove` on it because hard
rule #1 requires explicit permission for any removal, including of a scratch worktree, and this
one lives entirely inside the scratchpad directory. Flagging it rather than deleting it silently.

## Contract walk

| Item | Status | Evidence |
|---|---|---|
| C-001 | ✅ ticked, confirmed | `requirement_terms.yaml` exists with `version: 2`; `term_list.py::load_requirement_terms` returns a pydantic model; `grep -n 'python\|kubernetes\|se valorará' src/cv_writer/ingestion/requirements.py` → checked, no literal match (see `test_requirements_module_holds_no_vocabulary_literals`) |
| C-002 | ✅ ticked, confirmed with the shape note above | snapshot `==` for skills/seniority/work_models; no-loss + expected-value split for languages/section_markers, judged equivalent strength |
| C-003 | ✅ ticked, confirmed | `test_requirement_sections.py`, both languages, both zones, both directions (in the right zone / not in the other) |
| C-004 | ✅ ticked, confirmed | all 5 native names, both value and `source_phrase` |
| C-005 | ⬜ **open, matches spec's own tracking** — fixture and test do not exist; `T-005` is explicitly `BLOCKED` in `contract.md` pending Gustavo supplying the redacted posting text | no evidence, as expected |
| C-006 | ✅ ticked, confirmed | AST scan (structural) + socket-killed run (behavioural) + repeatability check |

5 of 6 contract items are genuinely discharged with real evidence. C-005 is not discharged, and
the contract itself already marks it `[ ]` rather than `[x]` — this validation is not surfacing
a surprise, it is confirming the contract's own honesty about its blocked item.

## Ranked gaps

1. **Surviving mutant: `RequirementTermList.as_mapping`'s unknown-group `ValueError` is untested**
   — `src/cv_writer/ingestion/term_list.py:81-82`. No test in
   `tests/unit/ingestion/test_term_list.py` calls `as_mapping` with an invalid group name; the
   guard can be silently broken (see mutation 4). Not tied to a numbered AC or contract Check, so
   it does not block this feature's five closable criteria, but it is real dead-sensor territory
   in a module whose stated design goal is "fail loudly." Suggest a follow-up unit test, not a
   re-open of this feature.
2. **AC-005 / C-005 — zero coverage, by design, tracked as blocked.** Not ranked as a defect per
   this run's scope; recorded here only so the report is honest that the feature is five-sixths
   closed, not six-sixths. `tests/integration/ingestion/test_real_posting.py` and
   `tests/integration/ingestion/fixtures/posting_es_redacted.txt` do not exist. Needs Gustavo's
   redacted posting text before `T-005` can start.
3. **Spec-precision observation, not a gap**: C-002's Check text describes one uniform snapshot
   `==` for "the four pre-migration dictionaries and the two marker tuples," but two of those six
   groups (languages, section_markers) are necessarily asserted differently because this same
   feature changes their content. The implementation's split (no-loss + expected-value-`==`) is
   discrimination-tested and holds the same strength; the contract's Check wording just didn't
   anticipate its own feature editing two of the six things it asked to snapshot. No action
   needed beyond this note — a future contract for a similarly self-modifying migration should
   phrase the Check per-group rather than as one blanket description.

## Lessons

- **L-006 (candidate)** — When running tests against a `git worktree` copy for mutation testing,
  confirm the interpreter actually resolves the package to the worktree, not to an editable
  install's `.pth` target. **Because:** the shared `.venv`'s `__editable__.cv_writer-0.1.0.pth`
  points at the main repo's `src/`, so the first mutation run silently tested unmutated code and
  reported a false "all tests still pass" — caught only by checking `cv_writer.__file__` before
  trusting the result. Fix: set `PYTHONPATH` to the worktree's `src/` directory (ahead of site-packages) for every
  test run against a worktree, and verify with `python -c "import cv_writer; print(cv_writer.__file__)"`
  before treating any mutation result as real.
