# AI Harness Contract

This file is read by the AI (Claude Code or compatible) at the start of every session in this
repo. It's the contract for how the AI is allowed to work here. Every project scaffolded from
this harness inherits this file as a starting point — edit it per-project as needed, but don't
weaken the hard rules below without re-confirming with a human.

## Who this is for

This harness is built for **build-to-learn** development: the human maintainer is a beginner
learning the *whats* and *whys* of software engineering, not just shipping features fast. AI
collaborators should optimize for the human understanding each decision, not just for the
fastest path to green tests. Prefer explaining trade-offs over silently picking one.

## What this repo is

Two things at once, deliberately:

1. **A harness** — the reusable operating environment for AI-assisted development (this file,
   `AGENTS.md`, `.claude/`, `.specs/`, `scripts/`, CI). This is the part you fork into future
   projects.
2. **`cv-writer`** — a concrete application under `src/cv_writer/`, built by that harness. It is
   the harness's own proving ground: if the loop can't carry a real feature, the loop is wrong.

## The four pillars

Everything in this repo serves one of four roles. Know which one you're looking at.

| Pillar | Role | Where it lives |
|---|---|---|
| **Feed-forward** | Guidance given *before* execution, to reduce ambiguity | `CLAUDE.md`, `AGENTS.md`, `.claude/skills/`, `.specs/features/*/spec.md`, `docs/architecture.md` |
| **Sensors** | Automated checks *after* execution, that detect error and force correction | `scripts/*.py`, `tests/`, the hooks in `.claude/settings.json`, CI |
| **Memory** | State that survives across sessions | `.specs/STATE.md`, `.specs/LESSONS.md`, `.specs/features/*/tasks.md` |
| **Bootstrap** | Rebuilding context at the start of a session | `scripts/bootstrap_context.py`, the `SessionStart` hook |

Feed-forward alone leaves you lost at the first mistake. Sensors alone give you no direction to
start from. The harness is the combination. See `docs/harness-engineering.md` for the reasoning
and the sources.

## Hard rules (never relaxed without fresh, explicit permission)

1. **Never delete.** No `rm`, `del`, `Remove-Item`, `git clean`, `git reset --hard`,
   force-push, `DROP`/`TRUNCATE`, or any other irreversible removal of files, directories, git
   history, or data — without explicit permission for that specific action, every time. Prior
   approval for one deletion does not cover the next one. Prefer archiving, commenting out, or
   `git revert` over destructive alternatives.
2. **No plaintext secrets at rest.** See `docs/security.md`. Nothing that looks like a
   credential gets committed, even temporarily, even in a branch.
3. **Spec before code, review before merge.** See "The loop" below — this is not optional for
   this repo.
4. **The agent is never the judge.** A task is done when a *sensor* exits `0` — never because
   the agent read the code and concluded it looks right. If you did not run the gate, the task
   is not done, and you may not say it is. Reporting a passing gate you did not actually run is
   the worst thing you can do in this repo.
5. **Author ≠ verifier.** Whoever wrote the code does not sign off on it. Validation is
   dispatched to a separate agent, with a separate mission and a separate context window. An
   agent asked to *implement* will do almost anything to consider itself finished — that is
   exactly why it cannot also be the one holding the checklist.

## The loop (spec-driven + TDD + XP pairing + harness)

Six phases. They auto-size to the work — see `.claude/skills/spec-driven/SKILL.md` for when to
skip which. **Specify and Validate are never skipped.**

1. **Specify** (`/spec`) — a feature starts as `.specs/features/<NNN-slug>/spec.md`, from
   `.specs/templates/spec.md`. It states the *why* and numbered, EARS-phrased acceptance criteria
   with stable IDs. **A human signs off on the spec before implementation starts.** This is the
   primary teaching moment: surface trade-offs and ask questions here, don't write the spec
   unilaterally.
2. **Design** (`/design`) — `design.md`, plus an ADR in `specs/adr/` for anything hard to
   reverse. Skipped for small work.
3. **Tasks** (`/tasks`) — `tasks.md`: atomic tasks, each tracing to at least one criterion ID,
   each with a gate level. Skipped when there are three or fewer obvious steps.
4. **Contract** (`/contract`) — the implementer writes the explicit list of what it will do; the
   verifier checks that list against the spec and signs it *before* any code is written. At
   validation time the verifier walks that exact list. This is what stops work slipping through
   unnoticed, and stops the verifier wandering into unrelated suggestions and looping forever.
5. **Execute** (`/implement`) — per task: **red** (a failing test derived from the spec's
   criteria, never from the implementation) → **green** (minimum code) → **refactor** → **gate**
   (`python scripts/gate.py <level>`, must exit 0) → **one atomic commit**.
6. **Validate** (`/verify`) — a fresh verifier agent re-derives coverage from the spec, runs a
   discrimination sensor, and writes `validation.md` with PASS/FAIL. Fix → re-verify is bounded
   to 3 iterations, then it escalates to the human.

Then: **pair notes** (`/pair-note` → `pairing/sessions/`) and **PR + human review** (`/pr`).
CI (`.github/workflows/ci.yml`) must pass. A human reviews the diff before merge — treat that as
a teaching checkpoint: comments should explain, not just approve or reject.

## Commands

Primary shell is **PowerShell on Windows**. A Bash tool (Git Bash) is also available; each takes
its own syntax. The virtualenv lives at `.venv/` and is *not* auto-activated — call its
interpreter by path.

```
# The gate — the only thing allowed to declare code correct
python scripts/gate.py quick     # ruff + unit tests
python scripts/gate.py full      # ruff + every test (unit, integration, e2e)
python scripts/gate.py build     # full + architectural boundary checks

# Underlying tools, if you need them directly
.venv/Scripts/python.exe -m pytest tests -q
.venv/Scripts/python.exe -m ruff check src tests

# Session state
python scripts/bootstrap_context.py   # where am I? (runs automatically at SessionStart)
python scripts/handoff.py             # write the handoff snapshot before you stop
```

`tests/` mirrors `src/` 1:1. Every test cites the criterion ID it proves; if you can't say which
criterion a test proves, it's probably testing the wrong thing.

## Model routing

Spend high-reasoning capacity where ambiguity and consequence are high; use a faster tier where
the work is mechanical. Two rules of thumb: **when unsure, size up, not down** — an under-powered
agent on ambiguous logic produces gaps the verifier then has to catch, which costs more than
paying for reasoning once. And **the verifier is never the cheapest tier**; a weak verifier
defeats hard rule #5.

| Work | Agent | Model |
|---|---|---|
| Orchestrating the loop | main session | `opus` |
| Specify — highest ambiguity; a bad spec poisons everything downstream | `spec-author` | `opus` |
| Design and ADRs — hard-to-reverse structural decisions | `architect` | `opus` |
| Task breakdown — structured but judgment-heavy | `task-planner` | `sonnet` |
| Writing code against a signed contract | `implementer` | `sonnet` |
| Validating code adversarially | `verifier` | `sonnet` |
| Settled-pattern scaffolding: DTOs, config, wiring, PR bodies | `scaffolder` | `haiku` |
| Summarising a session into notes | `pair-scribe` | `haiku` |

This is advisory routing, not a gate. No commit or verification step depends on it.

## Execution posture

Full local execution (running tests, scripts, dev servers) is fine without asking each time.
Destructive operations are covered by hard rule #1 above regardless of general trust level.
Outward-facing actions (pushing to remote, opening PRs, calling external APIs with real
credentials) should be confirmed first unless the human has clearly delegated that step.

Several hooks in `.claude/settings.json` **block** rather than warn: a malformed commit message,
a commit with a red gate, an edit to `src/` with no signed-off spec in play. Each refusal prints
its own bypass instructions. Bypassing is allowed; bypassing *silently* is not — every bypass is
logged to `.specs/STATE.md`.

## Folder map

See `README.md` for the full folder-by-folder explanation.
