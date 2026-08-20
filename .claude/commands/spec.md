---
description: Specify phase — write or refine a feature spec with EARS criteria, then stop at human sign-off
argument-hint: <NNN-slug> [what the feature is about]
model: opus
---

Run the **Specify** phase of the loop in `.claude/skills/spec-driven/SKILL.md` for: **$ARGUMENTS**

Dispatch the `spec-author` subagent. Give it:

- the feature slug and everything the user said about it
- the instruction to read `.specs/LESSONS.md` first
- the instruction to scan `src/` for what already solves part of this before proposing anything new

The spec goes to `.specs/features/<slug>/spec.md`, from `.specs/templates/spec.md`.

When it returns:

1. Run `python scripts/validate_spec.py .specs/features/<slug>/spec.md`. If it exits non-zero,
   send the findings back to the agent rather than fixing them yourself.
2. Set `- **Feature:** <slug>` and `- **Phase:** specify` under `## Current` in `.specs/STATE.md`.
3. Present to the user: the criteria, the trade-offs weighed, the assumptions made, and any open
   questions — especially blocking ones.

**Then stop.** Do not tick the sign-off boxes and do not move to Design. A human signs off; that
is the teaching checkpoint, and the `PreToolUse` hook on `src/**` enforces it.
