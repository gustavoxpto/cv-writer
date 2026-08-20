# Tasks: <NNN-slug>

- **Spec:** `.specs/features/<NNN-slug>/spec.md`
- **Status:** planning | executing | complete

<!--
Every task is atomic: one deliverable, independently verifiable, independently committable,
one commit. Every task traces to at least one AC-NNN, or it should not exist.
Validate with: python scripts/validate_tasks.py .specs/features/<NNN-slug>/tasks.md
-->

## Gate commands

| Level | Runs | Use when the task… |
|---|---|---|
| `quick` | ruff + unit tests | touches unit-tested code only |
| `full` | ruff + unit + integration + e2e | touches integration or e2e behaviour |
| `build` | full + architectural boundary checks | is the last task in a phase, or touches no tests (config, wiring) |

Run as `python scripts/gate.py <level>`. Non-zero exit means STOP and fix. Never lower a task's
gate level to make it pass.

## Phase 1 — <name>

- [ ] **T-001** — <one deliverable, imperative>
  - **Covers:** AC-001, AC-002
  - **Files:** `src/…`, `tests/unit/…`
  - **Gate:** quick
  - **Done when:** <observable outcome a sensor can confirm>

- [ ] **T-002** — <…>
  - **Covers:** AC-003
  - **Files:** `…`
  - **Gate:** quick
  - **Done when:** <…>

## Phase 2 — <name>

- [ ] **T-003** — <…>
  - **Covers:** AC-004
  - **Files:** `…`
  - **Gate:** full
  - **Done when:** <…>

## Coverage matrix

Every criterion in the spec appears here, against at least one task. A criterion with no task is
a planning bug, not an acceptable omission.

| Criterion | Task(s) | Test level |
|---|---|---|
| AC-001 | T-001 | unit |
| AC-002 | T-001 | unit |
| AC-003 | T-002 | unit |
| AC-004 | T-003 | integration |

## Execution notes

Append as you go — what was harder than planned, what got deferred, what the gate caught.
This is the running memory for anyone resuming mid-feature.
