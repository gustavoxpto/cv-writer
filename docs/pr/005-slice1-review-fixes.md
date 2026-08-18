# PR body — CV Writer slice 1: code-review fixes (profile package)

Ready to paste into GitHub.
Branch: `worktree-streamed-chasing-mango` → `main`. Title: `fix(001): address slice 1 code-review findings (profile package)`.

---

## What & why

`/code-review` of slice 1 (merged as PR #1) found 5 issues in `src/cv_writer/profile/`: 2 confirmed bugs and 3 lower-severity quality/data-integrity notes. This PR fixes all 5, each with a failing test first (reproduced against the pre-fix code) and the minimal fix to turn it green.

## What's in it

1. **Uncaught crash on non-UTF-8 `profile.yaml`** (`loader.py`) — `load_profile()` only caught `OSError` around reading the file. `UnicodeDecodeError` is a `ValueError` subclass, so a cp1252-encoded file (plausible for a hand-edited profile with accented PT characters) crashed with a raw traceback instead of `ProfileValidationError`. Now caught alongside `OSError`.
2. **Whitespace-only required strings passed validation** (`models.py`) — `Field(min_length=1)` alone lets `" "` through since it satisfies length 1 without stripping. Introduced a shared `ProfileModel` base (`model_config = ConfigDict(str_strip_whitespace=True)`) all eight models now inherit from, so Pydantic strips before length-validating.
3. **No `start_date <= end_date` check on job histories** (`models.py`) — a typo'd date swap loaded silently. Added a `model_validator(mode="after")` on `JobHistory` rejecting an inverted range (skipping the check when `end_date == "present"`).
4. **Dead guard in `profile_check()`** (`check.py`) — `len(history.bullets) > 1 and quantified_count == 1` had an always-true first half, since the schema already requires 3-5 bullets per history. Simplified to just the count check, with a comment explaining why.
5. **Test didn't test its own claim** (`test_schema_validation.py`) — `test_invalid_load_never_leaves_a_partial_profile_bound_in_the_caller` only verified Python assignment semantics (a local stays `None` if its RHS raises), true regardless of the loader's internals. Replaced with a test asserting `ProfileValidationError.__cause__` is a `pydantic.ValidationError` — the actual mechanism behind "raises before constructing."

## Acceptance criteria covered

No new criteria — this is a fix-forward pass on slice 1's criterion 1 guarantee ("fails with a clear error naming the field/path, never a partial profile, never a crash").

## Learning notes

- **A guard clause that's always true is worse than no guard.** It reads as intentional defensiveness against a case that can't happen, sending the next reader looking for a reason that doesn't exist. Removing it and commenting why the remaining condition suffices is more honest than leaving dead logic "just in case."
- **A test's name is a claim, and pytest won't check it for you.** The rewritten test asserts a fact tied to the actual mechanism (`ValidationError` as `__cause__`) instead of a fact that would hold true under any implementation.

## Verification

- 3 new tests + 1 rewritten test + 1 new fixture (`inverted_date_range.yaml`)
- `pytest tests/unit`: 50/50 passed
- `pytest tests/integration`: 54/54 passed
- `ruff check src tests`: clean

## Checklist

- [x] Tests written before implementation (TDD) — each of the 5 fixes has a failing test first
- [x] CI passing — `ruff check` clean, `pytest tests/unit tests/integration` green locally
- [x] No secrets committed
- [x] Pairing notes added — `pairing/sessions/2026-08-18-slice1-review-fixes.md`

### Reviewer: worth a look

1. **`ProfileModel.model_config = ConfigDict(str_strip_whitespace=True)`** applies to *every* string field on every model, including ones where whitespace might theoretically be meaningful (e.g. `Metric.value` free-form strings) — confirm that's the right scope rather than opting in field-by-field.
2. This branch was created from `main` post-slice-3-merge, not from the original `feat/001-slice1-profile-core` branch (already merged) — it's a fresh fix-forward branch, not a reopened PR #1.
