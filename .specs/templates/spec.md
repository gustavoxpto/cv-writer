# Spec: <feature name>

- **ID:** NNN-short-slug
- **Status:** draft
- **Size:** small | medium | large | complex
- **Author:** <human + AI pairing session>
- **Date:** <YYYY-MM-DD>

<!--
Status must be one of: draft | signed-off | implemented
Size drives which phases run — see .claude/skills/spec-driven/SKILL.md:
  small    (<=3 files)        one-liner Why, skip Design, skip Tasks
  medium   (clear, <10 tasks) brief Why, skip Design, Tasks inline
  large    (multi-component)  full spec, Design, full Tasks breakdown
  complex  (ambiguous/new)    full spec + discussion, research, Design, phased Tasks
Validate with: python scripts/validate_spec.py .specs/features/<ID>/spec.md
-->

## Why

What problem does this solve, for whom? Not *what* to build yet — *why* it's worth building.
If this is replacing broken behaviour, describe the actual failure you observed, not a
hypothetical one.

## Acceptance criteria

Numbered, testable, and phrased in **EARS notation**. Every criterion gets a stable `AC-NNN` ID
that never changes once the spec is signed off — tasks, contract items, and tests all cite it.

Every criterion must contain the word **SHALL** and must have exactly one interpretation. Pick
the pattern that fits:

| Pattern | Shape | Use for |
|---|---|---|
| Ubiquitous | The system SHALL … | always-true invariants |
| Event-driven | WHEN <trigger>, the system SHALL … | discrete triggers |
| State-driven | WHILE <state>, the system SHALL … | behaviour during a state |
| Optional-feature | WHERE <feature is present>, the system SHALL … | gated capabilities |
| Unwanted-behaviour | IF <condition>, THEN the system SHALL … | errors and failure paths |

- **AC-001** — The system SHALL …
- **AC-002** — WHEN …, the system SHALL …
- **AC-003** — IF …, THEN the system SHALL …

### Criterion → test placement

| Criteria | Lives in |
|---|---|
| AC-00N … | `tests/unit/…` |
| AC-00N … | `tests/integration/…` |
| AC-00N … | `tests/e2e/…` |

## Out of scope

Explicitly list what this spec does *not* cover, to stop scope creep mid-implementation. A thing
listed here is a decision, not an oversight.

## Open questions

Anything genuinely undecided. Mark each blocking or non-blocking. **Blocking questions must be
resolved before sign-off**; non-blocking ones just get tracked.

- [ ] **OQ-1** (non-blocking) — …

## Sign-off

- [ ] Human has read this and understands the *why*, not just the *what*.
- [ ] Acceptance criteria are specific enough to write failing tests from.

*(Implementation does not start until both boxes are checked and Status is `signed-off`.
The `PreToolUse` hook on `src/**` enforces this.)*
