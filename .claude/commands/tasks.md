---
description: Tasks phase — break a signed-off spec into atomic, traceable, gated tasks
argument-hint: <NNN-slug>
model: sonnet
---

Run the **Tasks** phase for: **$ARGUMENTS**

Refuse to start if the spec is not signed off — check with
`python scripts/validate_spec.py .specs/features/<slug>/spec.md` and read its `Status`. Planning
work against an unsigned spec is planning work that may not survive review.

Dispatch the `task-planner` subagent with `spec.md`, `design.md` if it exists, and
`.specs/templates/tasks.md`.

When it returns:

1. Run `python scripts/validate_tasks.py .specs/features/<slug>/tasks.md`. Send any findings back
   to the agent.
2. Set `- **Phase:** tasks` in `.specs/STATE.md`.
3. Report the task count and the phase structure.

If there are more than ~8 tasks, **offer** to pack whole phases into batches of roughly 7 tasks
and run one implementer per batch, sequentially. Never split a phase across agents, never nest
agents, and **never spawn without an explicit yes**. Under ~8 tasks, execute inline.

Next: `/contract <slug>`.
