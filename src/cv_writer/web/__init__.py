"""The web UI (criteria 32-35, slice 5) — a localhost-only FastAPI + Jinja2 shell over the
domain core (profile, db, ingestion, matching, generation).

See specs/adr/0005-web-ui-shape.md for the shape decisions, and
tests/unit/web/test_core_has_no_web_imports.py for the mechanical proof that the direction of
imports only ever goes one way (criterion 34): this package may import the core packages; none
of them may import this one or any web framework.
"""
