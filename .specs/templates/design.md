# Design: <NNN-slug>

- **Spec:** `.specs/features/<NNN-slug>/spec.md`
- **Date:** <YYYY-MM-DD>

<!--
Only for size `large` or `complex`. Skip it for small and medium work — the absence of this file
is a signal that the phase was correctly skipped, not that someone forgot.

Anything here that is hard to reverse (a schema, a boundary, a dependency, a file format) also
gets a numbered ADR in specs/adr/ and is linked from this file. Design.md explains the shape;
the ADR records the decision and what was rejected.
-->

## Shape

What components exist, what each is responsible for, and how they talk. A diagram in text is
fine. Name real module paths — `src/cv_writer/…` — not abstractions.

## Boundaries

What must NOT depend on what, and why. These become architectural tests in `tests/unit/`, the
same way `tests/unit/web/test_core_has_no_web_imports.py` already enforces that core logic
cannot import the web layer.

## Decisions

| # | Decision | Alternatives rejected | Why | ADR |
|---|---|---|---|---|
| 1 | <…> | <…> | <…> | `specs/adr/000N-…md` or "not ADR-worthy" |

## Build-to-learn notes

The concept the maintainer should understand *before* the code lands, and why this shape was
chosen over the obvious one. If there is no trade-off worth explaining here, the design was
probably not needed.
