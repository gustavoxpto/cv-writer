---
description: Execute phase — red, green, refactor, gate, one atomic commit per task
argument-hint: <NNN-slug> [T-NNN or "next"]
model: sonnet
---

Run the **Execute** phase for: **$ARGUMENTS**

**Refuse to start unless all three hold.** Check them, do not assume them:

1. `spec.md` is signed off — `python scripts/validate_spec.py .specs/features/<slug>/spec.md`
2. `contract.md` is signed by the verifier — `python scripts/validate_contract.py .specs/features/<slug>`
3. `tasks.md` validates — `python scripts/validate_tasks.py .specs/features/<slug>/tasks.md`

If any fails, report which and stop. The `PreToolUse` hook on `src/**` will refuse the edits
anyway; better to say so now than to be blocked mid-task.

Set `- **Phase:** execute` in `.specs/STATE.md`.

Dispatch the `implementer` subagent for the named task, or the next unticked one. For settled-
pattern work — DTOs, config, wiring, migrations that copy an existing file — use `scaffolder`
instead; it is faster and cheaper, and it is instructed to hand back anything ambiguous.

Per task the agent runs: red (failing test derived from the criterion, not the implementation) →
green (minimum code, only the listed files) → refactor → `python scripts/gate.py <level>` →
tick the task in `tasks.md` → one atomic commit containing code, tests and that tick.

When it returns, take a compact summary only: tasks done with commit hashes, test counts,
deviations or blockers. No raw logs.

**If a gate failed, the next task does not start.** Decide: fix, or escalate to the user.

Once the last task is committed, run `/verify <slug>` — automatically, without asking. Validation
is never optional and never offered.
