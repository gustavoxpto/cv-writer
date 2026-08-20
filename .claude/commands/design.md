---
description: Design phase — component shape, boundaries, and an ADR for anything hard to reverse
argument-hint: <NNN-slug>
model: opus
---

Run the **Design** phase for: **$ARGUMENTS**

First check the spec's `Size`. If it is `small` or `medium`, say so and stop — this phase is
skipped, and the absence of `design.md` is the correct signal that it was.

Otherwise dispatch the `architect` subagent with `spec.md` and the relevant parts of `src/`.

Output: `.specs/features/<slug>/design.md`, plus a numbered ADR in `specs/adr/` for every
decision that is hard to reverse. One decision, one home — the ADR records the decision and what
was rejected; `design.md` explains the shape and links to it.

When it returns:

1. Confirm every component traces to a criterion. Anything that does not is either scope creep
   or a missing criterion — say which, and send it back to `/spec` if it is the latter.
2. Confirm each declared boundary names the architectural test that will enforce it. A boundary
   with no test is a preference. `tests/unit/web/test_core_has_no_web_imports.py` is the pattern.
3. Set `- **Phase:** design` in `.specs/STATE.md`.
4. Present the trade-offs to the user, not just the conclusion.
