# projetos — AI-powered dev harness core

A reusable, sustainable folder structure built around four principles: **peer programming**,
**extreme programming (XP)**, **test-driven development (TDD)**, and **spec-driven
development**. This is meant to be the template you fork/copy for future projects, not a
single-purpose app repo.

See `CLAUDE.md` for the contract the AI harness follows in this repo — read that first, it
governs how AI collaborators are allowed to operate here (including a hard no-delete-without-
permission rule).

## Folder map

| Folder | Purpose | Principle it serves |
|---|---|---|
| `specs/` | Feature specs, ADRs — the source of truth *before* code is written | Spec-driven dev |
| `specs/adr/` | Architecture Decision Records — numbered, immutable once accepted | Spec-driven dev |
| `specs/features/` | Living feature specs with acceptance criteria | Spec-driven dev |
| `tests/` | Mirrors `src/` 1:1; tests are written before the code they test | TDD |
| `src/` | Application code | — |
| `pairing/sessions/` | Driver/navigator session logs — what was tried, rejected, why | Peer programming |
| `docs/` | Architecture, onboarding, security posture, learning log | All |
| `docs/learning-log.md` | Beginner-facing: what you learned each session and why it mattered | Build-to-learn |
| `.github/` | Actions CI, CODEOWNERS, PR template | XP (continuous integration) |
| `scripts/` | Dev tooling (not app logic) | — |
| `infra/` | IaC / deploy config | — |
| `secrets/` | Encrypted-at-rest secrets only — see `docs/security.md` | Security |
| `.claude/` | AI harness settings (permissions, hooks) | Security |

## The workflow, in one line

**Spec (human sign-off) → failing test → minimal code → refactor → pair notes → PR (human
review) → merge.** Full detail in `CLAUDE.md`.

## Security posture

No plaintext secrets, ever, at rest. See `docs/security.md` for the actual mechanism and its
current status (some of it is a documented target, not yet wired up — see the TODOs there).

## Status

This is a fresh scaffold (2026-08-17). Not yet a git repo with a GitHub remote — that's a
deliberate next step for you to do explicitly (`git init`, create the GitHub repo, connect
CODEOWNERS to real usernames) rather than something done on your behalf.
