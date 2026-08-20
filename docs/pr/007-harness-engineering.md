## What & why

Adds the **harness engineering** layer: the sensor, memory and bootstrap pillars this repo was
missing, plus mission separation and model routing.

This PR does not implement a feature spec. It changes how features get built, so it is scoped as
a harness change rather than a slice of `specs/features/001-cv-writer.md`. Full rationale,
provenance and change ledger: **`docs/harness-engineering.md`**.

### The problem

A spec is pure feed-forward — it says what to do and never verifies it happened. That was the
whole of this repo's harness: zero hooks, zero subagents, zero skills, zero slash commands.
`.claude/` held only permission lists, and every step of the loop lived in prose in `CLAUDE.md`,
holding for exactly as long as an agent remembered it.

Mapped against the six known agent failure modes, spec-driven development had bought two of them:

| # | Failure mode | Before | After |
|---|---|---|---|
| 1 | One-shot hero | covered (delivery slices) | covered |
| 2 | Premature victory | covered (numbered criteria) | covered |
| 3 | Amnesia between sessions | **no** | `.specs/STATE.md` + `SessionStart` bootstrap |
| 4 | Done without really testing | **no** | `gate.py`, `pre_commit` hook, hard rule #4 |
| 5 | Single process, self-judgement | **no** | subagents with exclusive tools, hard rule #5 |
| 6 | Accumulated slop | **no** | `gate.py build`, CI `harness` job, `test_census.py` |

### What changed

- **`.specs/`** — `STATE.md` (append-only `## Decisions`, rewritable `## Handoff`, bypass log),
  `LESSONS.md` seeded with five lessons mined from existing pairing notes, five artifact
  templates, per-feature directories.
- **The contract phase** — the implementer writes the list of observable outcomes it will
  deliver; the verifier signs it against the spec *before any code exists*; at validation the
  verifier walks that exact list. Bounds both what gets silently skipped and what the verifier is
  allowed to raise.
- **Eight sensors in `scripts/`** — one gate, four artifact validators, a Conventional Commits
  checker, a test-count ratchet, a context bootstrap. Stdlib-only, so CI runs them without
  installing the project.
- **Five Claude Code hooks that block rather than warn.** `src/` is unwritable without a
  signed-off spec; a commit needs a valid message and a green gate. Each refusal prints its own
  bypass instructions and every bypass is logged to `STATE.md`.
- **Seven subagents with mutually exclusive tool sets** — `implementer` has no route to write
  `validation.md`; `verifier` cannot touch `src/` or `tests/`. Model tiers: `opus` to plan,
  `sonnet` to write and review code, `haiku` for deterministic repeats.
- **Ten slash commands**, one per phase plus `/resume` and `/handoff`.
- **CI** — `timeout-minutes: 20`, pip and Playwright caching, Python 3.10 → 3.12, a test-census
  step, and a new stdlib-only `harness` job validating feature artifacts on every PR.
- **Stale docs repaired** — `docs/architecture.md`, the `README` status section, `CODEOWNERS`.

## Acceptance criteria covered

None from spec 001 — this is harness work. It does add two hard rules to `CLAUDE.md`:

- **#4 — the agent is never the judge.** A task is done when a sensor exits `0`, never because
  the agent read the code and concluded it looks right.
- **#5 — author ≠ verifier.** Whoever wrote the code does not sign off on it.

`.specs/features/002-requirement-dictionary-expansion/spec.md` is retrofitted into the new format
(EARS criteria, stable `AC-NNN` IDs) and passes `validate_spec.py`. It deliberately sits at
`draft` — the loop halts at human sign-off, which is the new gate working on its first real
feature.

## Learning notes

**The sensors caught their own bugs twice, which is the argument for building them.**

`test_only_commits_are_inspected` failed on `git -C <path> commit`. The commit-guard regex
allowed `-flag` tokens between `git` and `commit` but not a flag carrying its own argument — any
commit issued that way would have walked straight past the gate. Fixed the hook, not the test.

Then spec 002 failed `validate_spec.py` on two criteria that plainly contain `SHALL`. The parser
read only a list item's first line, so any criterion that wrapped lost its verb. That one is
worse than a bug: left unfixed it would have taught us to write one-line criteria to keep the
validator quiet — the tool reshaping the work to suit itself. Fixed with `_item_text()` plus a
regression test.

**A stale guide is negative feed-forward.** `docs/architecture.md` described an empty scaffold
while `src/` held ~55 modules; the README denied having a git remote after five PRs had merged
through one; `CODEOWNERS` requested review from `@your-github-username`. Each cost tokens and
trust on every read.

**Still fuzzy:** whether `PreToolUse` on `src/**` reads as a guardrail or an obstacle in daily
use. The bypass log is the instrument — if it fills up, the gate is miscalibrated and should be
changed rather than routed around.

## Reviewer: worth a look

- **`scripts/hooks/pre_edit_src.py`** — the spec-before-code gate. It guards `src/` only, so the
  failing test stays writable before the code exists. Is that the right boundary?
- **`scripts/hooks/on_stop.py`** deliberately does **not** block, unlike the other four. A `Stop`
  hook that refuses to let a session end can trap it in a loop, and a memory nudge is not worth
  that risk.
- **`AD-001` in `.specs/STATE.md`** — spec 001 was *not* migrated into `.specs/`. It is signed
  off, implemented across five merged PRs, and cross-linked from six `docs/pr/*` files, five ADRs
  and six pairing notes. Judgement call: churn versus consistency.
- **Model routing is not from the source video** — it never discusses tiering. The table is
  sourced to the TLC skill's `references/sub-agents.md`, and `docs/harness-engineering.md` says
  so explicitly rather than presenting an invention as a finding.
- **`src/cv_writer/ingestion/requirements.py`** is untouched by this PR. The 2026-08-19 ad hoc
  widening is still uncommitted in the working tree; deciding its fate is separate work.

## Checklist

- [x] Spec — n/a, harness change. Spec 002 retrofitted and validating, awaiting human sign-off
- [x] Tests written before implementation (TDD) — 69 new tests in `tests/unit/scripts/`, each an
      injected fault the validator must reject
- [ ] CI passing — first run on this PR
- [x] No secrets committed (see `docs/security.md`)
- [x] Pairing notes added — `pairing/sessions/2026-08-20-harness-engineering.md`

Local: `python scripts/gate.py build` → **PASS** (345 tests, ruff clean, artifact validators
green).
