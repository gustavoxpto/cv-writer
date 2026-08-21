# Superseded

The current spec template is **`.specs/templates/spec.md`**.

It keeps this file's shape — Why / acceptance criteria / Out of scope / Open questions /
Sign-off — and adds what the sensors need to check it: stable `AC-NNN` criterion IDs, EARS
phrasing (`SHALL`), a `Size` that drives which phases run, and blocking vs non-blocking open
questions.

Validate a spec with `python scripts/validate_spec.py .specs/features/<slug>/spec.md`.

This file is kept as a pointer rather than removed, so older links still lead somewhere.
See `AD-001` in `.specs/STATE.md`.
