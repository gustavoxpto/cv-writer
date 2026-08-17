# PR body — CV Writer slice 1: profile core (001, criteria 1-5)

Ready to paste into GitHub once the remote exists and this pushes.
Branch: `feat/001-slice1-profile-core` → `main`. Title: `feat(001): slice 1 — profile core (criteria 1-5)`.

---

## What & why

Implements slice 1 of [`specs/features/001-cv-writer.md`](../../specs/features/001-cv-writer.md): criteria 1-5, the profile schema and its validation. No database, no UI, no LLM — those are slices 2-5. This is the first PR in this repo that ships real code, so it also carries the mechanical prerequisites the spec PR's own review notes flagged: `master` → `main` (CI triggers on `main` and would never have run otherwise), and `data/` added to `.gitignore` before any real profile data exists.

## What's in it

- **`src/cv_writer/profile/`** — Pydantic v2 models (`Profile`, `JobHistory`, `Bullet`, `Metric`, `Skill`, `Language`, `Education`, `Identity`), a YAML loader (`load_profile`) that turns both YAML-parse failures and schema-validation failures into one `ProfileValidationError` naming the offending field's path, and `profile_check()` — a pure function reporting two non-fatal nudges (an unevidenced skill, a job history where only one of several bullets is quantified).
- **`data/profile.example.yaml`** — a fake-data reference profile; a test asserts it stays schema-valid so it can't silently drift into teaching an invalid shape.
- **`specs/adr/0002-cv-writer-technical-shape.md`** — the ADR the spec deferred to before code. One real substitution: this environment only has Python 3.10.11, not the spec's named 3.12; recorded rather than silently matched or silently ignored.
- **`.github/workflows/ci.yml`** — replaces the placeholder echo with real `pip install -e ".[dev]"` → `ruff check` → `pytest` steps.
- **23 tests** in `tests/unit/profile/`, one fixture YAML per failure mode, each test docstring citing the criterion it proves.

## Acceptance criteria covered

Criteria 1-5 (spec section A): schema validation with field-path error messages (1), required job-history fields (2), 3-5 STAR bullets (3), at least one quantified metric per history with a non-fatal check for under-quantified histories (4), skills linked to evidencing histories with a non-fatal check for unevidenced ones (5). Criterion 6 (loading into the embedded DB) is slice 2.

## Learning notes

- **The error message is part of the API, not an implementation detail.** Criterion 1 asks for the offending field *and path* — Pydantic's `ValidationError.errors()` already carries a `loc` tuple; the loader's only real job is joining that into a dotted path instead of leaking a raw `pydantic.ValidationError` past the package boundary.
- **A quota needs a home that isn't the thing being counted.** The "at least one metric per history" and "skill evidence must reference a real history" invariants both live as `model_validator`s on `Profile`/`JobHistory` rather than on `Bullet`/`Skill`, because they're checks about relationships between siblings, not about one object in isolation — a child model validates before it knows what else exists in the list it's part of.
- **`profile_check()` is deliberately not part of `load_profile()`.** Loading has a two-outcome contract (valid `Profile`, or an exception); the check has a fundamentally different one (a list of warnings, always returned, never blocking). Collapsing them would make the loader's contract fuzzier for no benefit.

## Checklist

- [x] Spec in `specs/features/` signed off before implementation — `001-cv-writer.md`, criteria 1-5 targeted
- [x] Tests written before/alongside implementation (TDD) — 23 tests, each citing its criterion
- [x] CI passing — `ruff check` clean, `pytest tests/unit tests/integration` green locally; workflow now runs both instead of echoing a placeholder
- [x] No secrets committed — no credentials touched by this slice; `data/` (future personal data) is gitignored before `data/profile.yaml` exists
- [x] Pairing notes added — `pairing/sessions/2026-08-17-slice1-profile-core.md`, including a process note on a hard-rule miss (an unasked-for `rm` on a redundant scaffold file, caught and reverted before commit)

### Reviewer: worth a look

1. **Python 3.10 vs the spec's named 3.12** (ADR 0002) — confirm this is fine to keep riding on 3.10, or if 3.12 should be installed and the ADR revised.
2. **`Metric.value` is a free-form string**, not a parsed number — deliberate, per the ADR/pairing notes, to avoid inventing precision across incompatible formats (`+37%`, `R$1.2M`, `from 9 days to 2 days`). Worth confirming this doesn't make slice 3's matching/scoring harder than expected.
3. **CI was wired to run now** rather than waiting for slice 5 (where criterion 36 formally lives) — flag if that's not wanted yet for some reason.
