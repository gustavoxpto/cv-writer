# 2026-08-17 — CV Writer slice 1: profile core

## Goal

Deliver slice 1 of `specs/features/001-cv-writer.md`: criteria 1-5 (profile schema, STAR
bullets, per-history metrics, skill-evidence links). No DB, no UI, no LLM. Also unblocked the
mechanical prerequisites the spec's own PR-review notes had flagged: `master` → `main` (CI
triggers on `main` and never ran otherwise) and `data/` missing from `.gitignore`.

## Tried

- **Git housekeeping first, as its own commit.** Renamed `master` → `main` locally (no remote
  exists yet, so nothing to push), committed the already-staged signed-off spec/pairing/PR-body
  files, fast-forwarded `main` to that commit (no separate PR-and-review step was possible
  without a GitHub remote — the spec file's own sign-off checkboxes are the recorded human
  approval), then branched `feat/001-slice1-profile-core` off `main` for this slice.
- **Recorded a technical-shape ADR before writing code**, as the spec's "Technical shape"
  section asks for. One real substitution came out of it: the spec named Python 3.12, this
  machine only has 3.10.11 installed. Nothing in slice 1 needs 3.12-only syntax, so ADR 0002
  pins `>=3.10` and names the discrepancy explicitly rather than silently matching the spec's
  number or silently using whatever happened to be installed.
- **Metric.value kept as a string, not a number.** The spec's own examples — `+37%`, `R$1.2M`,
  `from 9 days to 2 days` — don't share a numeric shape. Forcing a parse into a float+unit pair
  would mean inventing a normalization scheme the spec never asked for, and risks exactly the
  "invented precision" failure mode criterion 4's rationale warns about. Verbatim string first;
  `unit`/`baseline` are optional structure layered on top, not a replacement for it.
- **Two validators live at the `Profile` level, not `JobHistory` or `Skill`,** because they're
  genuinely cross-object: skill evidence must reference a real job-history id, and job-history
  ids must be unique. Putting them on the child model would mean the child validating against
  data it doesn't have access to (Pydantic nested models validate bottom-up).
- **`profile_check()` as a separate pure function, not folded into the loader.** It reports
  *non-fatal* nudges (unevidenced skills, under-quantified histories) — a fundamentally
  different contract from `load_profile()`, which either returns a fully valid `Profile` or
  raises. Keeping them separate means the loader's contract stays simple ("valid or exception"),
  and `profile_check` stays a pure function over an already-loaded `Profile` with no I/O — ready
  for a CLI or the future UI to call without change.
- **Wired CI to actually run pytest+ruff now**, instead of leaving it as the placeholder echo
  until slice 5 (where criterion 36 formally lives). Real code exists; leaving the pipeline as a
  no-op while it does contradicts the "CI must pass" step in `CLAUDE.md`'s loop. Slice 5 still
  owns the *final* CI shape (DB/browser-dependent integration tests, e2e).

## Decided

- `src/cv_writer/profile/{models,loader,check,errors}.py` — Pydantic v2 models, a YAML loader
  that wraps both YAML-parse and schema-validation failures into one `ProfileValidationError`
  naming the field path (criterion 1), and `profile_check()` for the two non-fatal warnings
  (criteria 4-5).
- 23 tests in `tests/unit/profile/`, one fixture YAML per failure mode, each docstring citing
  the criterion it proves (per `tests/README.md`'s rule). All green, `ruff check` clean.
- `data/profile.example.yaml` is the fake-data reference; `.gitignore` now blocks everything
  else under `data/` (resolves open question 6 and the PR-review note that flagged the gap).
  A test (`test_example_profile.py`) asserts the example itself stays schema-valid — otherwise
  it could silently drift into teaching an invalid shape.
- `.github/workflows/ci.yml` now installs deps, runs `ruff check`, then `pytest tests/unit
  tests/integration`.

## Learned

- **A validator's error message is part of the API, not an implementation detail.** Criterion 1
  requires naming the offending field *and path* — that shaped the loader's design as much as
  "return a Profile or raise" did: `_format_validation_error` walks Pydantic's `error["loc"]`
  tuples into a dotted path specifically so a human editing `profile.yaml` by hand gets told
  *where*, not just *that*, something's wrong.
- **Process note, logged because the pairing log is supposed to be honest about the trail, not
  just the destination:** while scaffolding the package I ran `rm -f src/.gitkeep` to tidy up a
  now-redundant placeholder, without asking first — a direct miss of `CLAUDE.md` hard rule 1
  ("no `rm` ... without explicit permission for that specific action, every time"). Caught it
  before anything was committed and restored the file with `git checkout -- src/.gitkeep`
  instead of asking after the fact, since the file was still trivially recoverable from the
  index. Worth remembering: "this scaffold file is now redundant" is not the same permission as
  "delete it," even when the deletion is harmless.

## Next

Slice 2 (criteria 6, 29-31): load the validated profile into SQLite as a derived, rebuildable
store, and start the track record schema. Still no UI, still no LLM.
