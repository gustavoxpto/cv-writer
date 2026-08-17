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

## The loop (spec-driven + TDD + XP pairing)

1. **Spec** — a feature starts as a doc in `specs/features/`, using
   `specs/templates/spec-template.md`. It states the *why*, the acceptance criteria, and open
   questions. **A human signs off on the spec before implementation starts.** This is the
   primary teaching moment: the AI should surface trade-offs and ask questions here, not just
   write the spec unilaterally.
2. **Red** — write a failing test in `tests/` (mirrors `src/` structure) that encodes one
   acceptance criterion from the spec.
3. **Green** — write the minimum code in `src/` to pass it.
4. **Refactor** — clean up with tests green. Explain *why* a refactor is worth it, not just
   that it happened.
5. **Pair notes** — log non-obvious decisions from the session in `pairing/sessions/` (see that
   folder's README). This is the human+AI "driver/navigator" trail — what was tried, what was
   rejected, and why.
6. **PR + review** — open a PR against `main`. CI (`.github/workflows/ci.yml`) must pass.
   **A human reviews the diff before merge** — again, treat this as a teaching checkpoint:
   comments should explain, not just approve/reject.

## Execution posture

Full local execution (running tests, scripts, dev servers) is fine without asking each time.
Destructive operations are covered by hard rule #1 above regardless of general trust level.
Outward-facing actions (pushing to remote, opening PRs, calling external APIs with real
credentials) should be confirmed first unless the human has clearly delegated that step.

## Folder map

See `README.md` for the full folder-by-folder explanation.
