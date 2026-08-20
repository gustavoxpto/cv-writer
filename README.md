# projetos — AI dev harness, and the app it built

Two things in one repo, deliberately.

**The harness** — a reusable operating environment for AI-assisted development, built on peer
programming, extreme programming (XP), test-driven development (TDD), spec-driven development,
and **harness engineering**: the idea that guidance which is not enforced by code is not
guidance, it is a suggestion. This is the part you fork into the next project.

**`cv-writer`** — a real application under `src/cv_writer/` that turns a job posting into a
truthful, well-matched CV. It is the harness's proving ground: if the loop cannot carry a real
feature end to end, the loop is wrong.

Read `CLAUDE.md` first — it is the contract every AI collaborator operates under here, including
a hard no-delete-without-permission rule. `docs/harness-engineering.md` explains why the harness
is shaped the way it is.

## The four pillars

| Pillar | Role | Where |
|---|---|---|
| **Feed-forward** | guidance *before* execution | `CLAUDE.md`, `AGENTS.md`, `.claude/skills/`, `.specs/features/*/spec.md` |
| **Sensors** | automated checks *after* execution | `scripts/*.py`, `tests/`, hooks in `.claude/settings.json`, CI |
| **Memory** | state that survives a session ending | `.specs/STATE.md`, `.specs/LESSONS.md`, `pairing/sessions/` |
| **Bootstrap** | rebuilding context at session start | `scripts/bootstrap_context.py` |

A spec alone tells an agent what to do but never checks that it happened. Sensors alone give it
nothing to aim at. The harness is the combination.

## Folder map

| Folder | Purpose | Principle |
|---|---|---|
| `.specs/` | Live feature work: spec → design → tasks → contract → validation, plus `STATE.md` and `LESSONS.md` | Spec-driven, memory |
| `.specs/templates/` | The five artifact templates the validators enforce | Feed-forward |
| `specs/adr/` | Architecture Decision Records — numbered, immutable once accepted | Spec-driven |
| `specs/features/` | Spec 001, frozen as a historical record (see `AD-001`) | — |
| `scripts/` | The sensors: the gate, the artifact validators, bootstrap, hooks | Harness engineering |
| `tests/` | Mirrors `src/` 1:1; written before the code they test | TDD |
| `src/` | Application code (`cv_writer`) | — |
| `pairing/sessions/` | Driver/navigator logs — what was tried, rejected, why | Peer programming |
| `docs/` | Architecture, harness rationale, security, onboarding, PR bodies | All |
| `.claude/` | Skill, subagents (with model tiers), slash commands, hooks, permissions | Harness engineering |
| `.github/` | CI, CODEOWNERS, PR template | XP (continuous integration) |
| `infra/` | IaC / deploy config | — |
| `secrets/` | Encrypted-at-rest secrets only — see `docs/security.md` | Security |

## The loop, in one line

**Specify (human sign-off) → Design → Tasks → Contract (verifier-signed) → Execute (red, green,
refactor, gate, atomic commit) → Validate (independent verifier) → pair note → PR (human review)
→ merge.**

Slash commands for each: `/spec`, `/design`, `/tasks`, `/contract`, `/implement`, `/verify`,
`/pair-note`, `/pr`, plus `/resume` and `/handoff`. Full detail in `CLAUDE.md` and
`.claude/skills/spec-driven/SKILL.md`.

## Getting oriented

```
python scripts/bootstrap_context.py   # what feature is live, what phase, what is left
python scripts/gate.py quick          # ruff + unit tests
python scripts/gate.py full           # ruff + every test
```

The venv is at `.venv/` and is not auto-activated: `.venv/Scripts/python.exe -m pytest tests -q`.

## Security posture

No plaintext secrets, ever, at rest. See `docs/security.md` for the mechanism and its current
status — some of it is a documented target, not yet wired up.

## Status

Five slices of `cv-writer` merged (spec 001, criteria 1–37). Harness engineering layer added
2026-08-20 — see `docs/harness-engineering.md` for what changed and why. Remote is
`gustavoxpto/cv-writer`; branch protection on `main` is still a repo-settings TODO
(`docs/security.md`).
