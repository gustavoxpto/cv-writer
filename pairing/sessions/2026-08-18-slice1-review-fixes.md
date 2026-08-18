# 2026-08-18 — CV Writer slice 1: code-review fixes

## Goal

`/code-review` of slice 1 (`profile` package, merged as PR #1) surfaced 2 confirmed bugs and 3
lower-severity issues. Fix all 5, TDD-style: a failing test per issue first, then the minimal
code to turn it green.

## Tried

- **Non-UTF-8 file crash.** `load_profile()` only caught `OSError` around `path.read_text()`.
  `UnicodeDecodeError` is a `ValueError` subclass, not an `OSError`, so a cp1252-encoded
  `profile.yaml` (plausible for a hand-edited file with accented PT characters, per the example
  profile's own instructions) crashed with a raw traceback instead of `ProfileValidationError`.
  Reproduced with a fixture written as cp1252 bytes containing "não" before fixing — the test
  failed with the exact `UnicodeDecodeError` the review predicted.
- **Whitespace-only required strings.** `Field(min_length=1)` alone lets `" "` through since
  length-1 satisfies the constraint without stripping first. Considered a per-field validator,
  but every string field across every model has the same problem, so introduced one shared
  `ProfileModel` base with `model_config = ConfigDict(str_strip_whitespace=True)` and had all
  eight models inherit from it instead of `BaseModel` directly — Pydantic strips before
  length-validating, so `min_length=1` now does what it already looked like it did.
- **Inverted job-history dates.** No validator connected `start_date` and `end_date` at all — a
  typo'd swap loaded silently. Added a third `model_validator(mode="after")` on `JobHistory`
  alongside the existing metric-presence one; skips the check when `end_date == "present"` since
  that's a valid literal, not a date to compare.
- **Dead guard in `profile_check()`.** `len(history.bullets) > 1 and quantified_count == 1` — the
  first half is always true because the schema already requires 3-5 bullets
  (`MIN_BULLETS_PER_HISTORY`). Simplified to just the count check and left a comment explaining
  why the guard isn't needed, so a future reader doesn't wonder if it's protecting against
  something real.
- **Test that didn't test its own name.**
  `test_invalid_load_never_leaves_a_partial_profile_bound_in_the_caller` only verified that a
  Python local variable stays `None` when its assignment's RHS raises — true regardless of what
  `load_profile()` does internally. Replaced it with a test that pins the actual mechanism:
  asserts the raised `ProfileValidationError.__cause__` is a `pydantic.ValidationError`, which is
  what actually guarantees "raises before constructing" (Pydantic's `model_validate()` contract),
  rather than restating a Python semantics fact that would hold under any implementation.

## Decided

- `src/cv_writer/profile/loader.py` — catch `UnicodeDecodeError` alongside `OSError`.
- `src/cv_writer/profile/models.py` — new `ProfileModel` base (whitespace-stripping config);
  `JobHistory._require_start_before_end` validator.
- `src/cv_writer/profile/check.py` — dropped the always-true half of the `single_quantified_bullet`
  guard.
- 3 new tests (`test_schema_validation.py` x2, `test_job_history.py` x1) plus one rewritten test;
  1 new fixture (`inverted_date_range.yaml`). 26/26 profile tests green, 50/50 unit + 54/54
  integration suite-wide, `ruff check` clean.

## Learned

- **A guard clause that's always true either way is worse than no guard** — it reads as
  intentional defensiveness against a case that can't happen, which sends the next reader
  looking for a reason that doesn't exist. Removing it and commenting *why* the remaining
  condition is sufficient is more honest than leaving dead logic "just in case."
- **A test's name is a claim.** `test_invalid_load_never_leaves_a_partial_profile_bound_in_the_caller`
  read as testing the loader's guarantee, but only exercised Python variable-assignment
  semantics. The fix wasn't more assertions — it was asserting a fact that's actually tied to
  the mechanism (`ValidationError` as `__cause__`) instead of a fact that would hold no matter
  what the mechanism was.

## Next

No change to slice 2/3 scope — this was a fix-forward pass on already-merged slice 1 code found
by `/code-review`, done on a fresh worktree branch off the current work rather than reopening
PR #1.
