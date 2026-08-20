---
name: spec-driven
description: The six-phase feature loop for this repository — Specify, Design, Tasks, Contract, Execute, Validate — with human sign-off, deterministic gates, and an independent verifier. Use when planning a feature, breaking one into tasks, implementing against a spec, or validating that an implementation actually meets it. Triggers on "spec", "new feature", "break this down", "implement", "verify", "validate", "is this done".
---

# Spec-driven, with a harness around it

A spec tells an agent what to do. It does not check that it happened. That gap is where the
familiar failures live: a feature marked done that was never really tested, a session that
starts from nothing because the last one left no trace, quality lost a few percent at a time
until the codebase is not worth extending.

So: **feed-forward** (spec, design, contract) says what should happen; **sensors**
(`scripts/gate.py`, the validators, the verifier) prove it did. Neither half works alone.

## Phases

```
SPECIFY  →  DESIGN  →  TASKS  →  CONTRACT  →  EXECUTE  →  VALIDATE
required   optional*  optional*  required     required    required
```

`*` skipped when the work does not need them. **Absence of a file is the signal that a phase was
skipped** — do not create an empty `design.md` to look thorough.

### Auto-sizing

| Size | Specify | Design | Tasks | Contract | Execute | Validate |
|---|---|---|---|---|---|---|
| **small** (≤3 files) | brief Why, 1–3 criteria | skip | skip | 2–3 items | inline | inline, 1 mutation |
| **medium** (clear feature, <10 tasks) | full spec | skip | inline in contract | full | per task | full report |
| **large** (multi-component) | full spec | yes + ADR | full breakdown | full | per task | full report |
| **complex** (ambiguous, new domain) | full spec + discussion first | research + ADR | phased breakdown | full | per task | expanded sensor |

When unsure, size up. An under-specified feature costs more at validation than it saved at
specification.

## 1. Specify → `.specs/features/<NNN-slug>/spec.md`

Agent: `spec-author` (opus). Template: `.specs/templates/spec.md`.

Load `.specs/LESSONS.md` first — several of those lines exist because a spec was thin.

Write acceptance criteria in EARS notation with stable `AC-NNN` IDs. Every criterion contains
**SHALL** and has exactly one reading:

| Pattern | Shape |
|---|---|
| Ubiquitous | The system SHALL … |
| Event-driven | WHEN <trigger>, the system SHALL … |
| State-driven | WHILE <state>, the system SHALL … |
| Optional-feature | WHERE <feature present>, the system SHALL … |
| Unwanted-behaviour | IF <condition>, THEN the system SHALL … |

**Facts you discover; decisions you ask.** This repo is build-to-learn — the human is here to
understand the trade-off, not to rubber-stamp a conclusion. Surface the alternatives you
considered and why you leaned one way. Record every assumption you had to make.

Gate: `python scripts/validate_spec.py <path>` must exit 0.
**Stop here.** A human ticks both sign-off boxes and sets `Status: signed-off`. The `PreToolUse`
hook on `src/**` enforces that; do not try to route around it.

## 2. Design → `design.md` (large / complex only)

Agent: `architect` (opus). Anything hard to reverse also gets a numbered ADR in `specs/adr/`.
Boundaries decided here become architectural tests — `tests/unit/web/test_core_has_no_web_imports.py`
is the pattern to copy.

## 3. Tasks → `tasks.md`

Agent: `task-planner` (sonnet). Template: `.specs/templates/tasks.md`.

Each task: one deliverable, independently verifiable, independently committable, one commit.
Each carries **Covers** (≥1 criterion ID), **Files**, **Gate** level, **Done when**.
A task that traces to no criterion is scope creep or a missing criterion — resolve which.

Gate: `python scripts/validate_tasks.py <path>`.

## 4. Contract → `contract.md`

The implementer writes it; the verifier signs it. Before any code exists.

Each item is an **observable outcome**, not a file or a task, with the **Check** the verifier
will run to confirm it. Two failures this prevents:

1. Work slipping through — at validation the verifier walks this exact list, item by item.
2. Verifier drift — without an agreed list a verifier starts raising unrelated improvements and
   the implementer chases them forever. Anything the verifier wants that is not here goes back
   into the spec as a new criterion; it does not get added at validation time.

Gate: `python scripts/validate_contract.py .specs/features/<feature>` and the signature box.

## 5. Execute

Agent: `implementer` (sonnet), or `scaffolder` (haiku) for settled-pattern work. Per task:

1. **Red** — write the failing test. Derive it from the criterion, never from the implementation
   you are about to write. Every criterion maps to at least one assertion, and each assertion
   targets the outcome the spec actually states.
2. **Green** — the minimum code to pass. Touch only the files the task lists.
3. **Refactor** — with tests green. Explain *why* the refactor is worth it.
4. **Gate** — `python scripts/gate.py <level>`. Non-zero means stop and fix.
5. **Commit** — tick the task in `tasks.md`, then commit code, tests and that tick together.
   Conventional Commits; the `PreToolUse` hook checks the message and re-runs the gate.

**Never** weaken an assertion, skip a test, or delete a test to make a gate pass. If a test is
genuinely wrong, say so and ask — do not fix it silently. `scripts/test_census.py` will notice
a vanished test either way.

## 6. Validate → `validation.md`

Agent: `verifier` (sonnet). **Author ≠ verifier** — dispatched fresh, with no memory of writing
the code. Template: `.specs/templates/validation.md`.

1. **Spec-anchored coverage.** Every criterion traced to `file:line` plus the assertion
   expression. Evidence or zero. Confirm the asserted value matches the spec's stated outcome;
   where the spec never stated one, flag a **spec-precision gap** rather than passing quietly.
2. **Assertion depth.** Reject tautologies, "no exception raised" as the only check, call-count
   assertions with no value check, happy-path-only against a criterion naming edge cases.
3. **Discrimination sensor.** Inject small behaviour-level faults in an **isolated scratch copy**
   — a temporary `git worktree` or file copies, never `git stash`, never the real tree — run the
   relevant tests, confirm they fail, discard. Afterwards `git status --porcelain` must match the
   pre-sensor baseline. 1–3 mutations normally; 5+ on anti-fabrication guarantees, security
   boundaries, or anything that writes data. A surviving mutant is a gap.
4. **Contract walk.** Every contract item ticked, or listed as a gap.
5. Write the report, score each check against its stated minimum, return PASS/FAIL.

The verifier does not write or fix code. Gaps go back to the implementer as fix tasks; that
loop is bounded to **3 iterations**, then escalate to the human.

Gate: `python scripts/validate_state.py <feature>`.

## Then

`/pair-note` (pairing note + a `LESSONS.md` line if something generalises), `/pr`, human review,
merge. Update `## Current` in `.specs/STATE.md` whenever you change phase — it is not inferred.

## Sub-agent delegation

Under ~8 tasks, run inline. Above that, offer to pack whole phases into batches of ~7 tasks each
and dispatch one agent per batch, sequentially — never split a phase across agents, never nest.
**Offer, then wait for a yes.** Never auto-spawn.

The verifier is different: it always runs, it is never offered, and it is never the cheapest
model tier. A weak verifier defeats the whole arrangement.

## Never

- Report a gate you did not run.
- Mark a task done because the code looks right.
- Validate code you wrote.
- Add work that no criterion asked for.
- Delete anything — see `CLAUDE.md` hard rule #1, every time, no exceptions carried forward.
