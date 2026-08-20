# Validation: <NNN-slug>

- **Verdict:** PASS | FAIL
- **Verifier:** `verifier` (must not be the agent that wrote the code — hard rule #5)
- **Date:** <YYYY-MM-DD>
- **Commit range:** `<sha>..<sha>`
- **Iteration:** 1 of max 3

<!--
Written by the verifier, never by the implementer. Evidence or zero: a criterion with no
file:line is NOT covered, however obvious it looks.
Validate with: python scripts/validate_state.py <NNN-slug>
-->

## Score

Each check has a stated minimum. The verdict is PASS only if every row passes.

| Check | Score | Minimum to pass | Result |
|---|---|---|---|
| Criterion coverage | 0/0 | 100% of criteria | — |
| Assertion depth | 0/0 | 100% non-shallow | — |
| Contract completion | 0/0 | 100% of contract items | — |
| Discrimination sensor | 0/0 killed | 100% of mutations killed | — |
| Gate (`gate.py build`) | — | exit 0 | — |

## Criterion evidence

| Criterion | Contract item | Evidence (`file:line`) | Asserted value matches the spec's stated outcome |
|---|---|---|---|
| AC-001 | C-001 | `tests/unit/…:NN` | yes / **spec-precision gap** |

Where the spec does not define a precise expected outcome, flag a **spec-precision gap** rather
than passing silently. A gap is a spec bug and goes back to Specify — it is not the implementer's
fault and not something to paper over with a looser assertion.

## Assertion depth

Rejected as shallow, and therefore not counted as coverage:

- tautologies (`assert True`, `assert x == x`)
- "no exception was raised" as the only check, unless that *is* the criterion
- call-count assertions with no check on the value produced
- happy path only, where the criterion names edge cases

For every field of a returned object, the assertion must target the field's **value**, not merely
that the call producing it happened.

## Discrimination sensor

Does the test suite actually detect breakage? Inject small behaviour-level faults, confirm the
tests fail, then discard.

**Run in an isolated scratch copy — never `git stash`, never the real working tree.** After the
run, `git status --porcelain` must match the pre-sensor baseline exactly.

| # | Mutation | File | Tests expected to fail | Killed? |
|---|---|---|---|---|
| 1 | <flip a condition> | `src/…` | `tests/…` | yes / **SURVIVED** |
| 2 | <change a return value> | `src/…` | `tests/…` | |
| 3 | <remove a required side effect> | `src/…` | `tests/…` | |

Standard features: 1–3 mutations. Critical paths (anti-fabrication guarantees, security
boundaries, data writes): 5 or more. **A surviving mutant is a gap, not a curiosity** — it means
a criterion has a test that cannot fail.

## Ranked gaps

Only present when the verdict is FAIL. Most severe first. Each becomes a fix task.

1. <gap> — <criterion or contract item> — `file:line` or "no evidence"

## Lessons

One or two lines worth carrying forward, appended to `.specs/LESSONS.md`. Not a summary of the
feature — a rule that would have prevented a gap found here.
