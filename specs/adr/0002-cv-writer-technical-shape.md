# ADR 0002: CV Writer technical shape

- **Status:** accepted
- **Date:** 2026-08-17

## Context

`specs/features/001-cv-writer.md` (signed off 2026-08-17) names a technical shape in its
"Technical shape" section and explicitly defers the ADR to before code is written. This record
exists to satisfy that gate, and to pin down one thing the spec left as a stated target rather
than a verified fact: the Python version.

## Decision

- **Python 3.10, not 3.12.** The spec named 3.12 as the target. The only interpreter available
  in this dev environment is **3.10.11** (checked via `python --version` / `py -0p`); no 3.12
  install exists here. Nothing in slice 1 (Pydantic v2, PyYAML, pytest) needs a 3.12-only
  language feature, so the substitution costs nothing now. Recorded here rather than silently
  matched, because the spec named a specific version deliberately and a future session
  shouldn't assume 3.12 is running. Revisit if a later slice needs something 3.10 doesn't have
  (e.g. improved `typing` syntax) — install 3.12 then rather than backporting workarounds.
- **Pydantic v2** for all domain models (`Profile`, `JobHistory`, `Bullet`, `Metric`, `Skill`,
  …). Validation errors already carry field path + message, which is most of what criterion 1
  ("fails with an error naming the offending field and path") needs for free; the loader wraps
  them in a domain-specific `ProfileValidationError` rather than leaking `pydantic.ValidationError`
  past the `profile` package boundary, so callers depend on our error shape, not a third-party
  library's.
- **PyYAML** to parse `data/profile.yaml` into a plain dict before Pydantic validates it — no
  YAML-specific validation library; malformed YAML (not just schema-invalid YAML) is caught at
  the parse step and re-raised through the same `ProfileValidationError` path.
- **pytest** + **ruff**, wired into CI per criterion 36. `pyproject.toml` is the single config
  file for both plus packaging (`src/` layout, `pip install -e .`).
- Deferred to their own slice, not decided here: **FastAPI + Jinja2** (slice 5, UI), **SQLite**
  (slice 2, track record + derived profile store), **headless Chromium** for PDF render and
  ingestion tier 2 (slice 3–4 — the spec's open question 2 flags a WeasyPrint spike first), and
  the `Rephraser` LLM interface (slice 4). Naming them here would commit code that doesn't exist
  yet to a choice slice 1 has no way to test.

## Consequences

- `pyproject.toml` pins `requires-python = ">=3.10"` rather than `>=3.12`; if a later slice
  needs 3.12+, that's a version bump here, not a silent contradiction with what's installed.
- Slice 1 has exactly three runtime dependencies (`pydantic`, `pyyaml`) plus two dev-only
  (`pytest`, `ruff`) — deliberately minimal, since no DB/UI/LLM exists yet (spec's own framing
  for this slice).
