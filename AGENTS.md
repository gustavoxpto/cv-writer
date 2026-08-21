# AGENTS.md

Cross-tool entry point for AI coding agents working in this repository.

**The contract is `CLAUDE.md`. Read it in full before doing anything.** This file exists so that
agents which look for `AGENTS.md` by convention (Codex, Cursor, Copilot, Antigravity, and others)
land on the same rules rather than inventing their own.

## The five rules you cannot break

1. **Never delete anything** without fresh, explicit, per-action human permission — no `rm`,
   `git clean`, `git reset --hard`, force-push, `DROP`. Prior approval never carries forward.
2. **No plaintext secrets at rest**, ever, even in a branch that gets squashed later.
3. **Spec before code, human review before merge.**
4. **You are never the judge of your own work.** A task is done when `python scripts/gate.py`
   exits `0`. Not when you have read the code and concluded it looks right.
5. **Author ≠ verifier.** Do not validate code you wrote.

## Where things are

| You need | Look at |
|---|---|
| The full contract and the loop | `CLAUDE.md` |
| What the current feature is, and where work stopped | `.specs/STATE.md` |
| Requirements with testable IDs | `.specs/features/<feature>/spec.md` |
| What was agreed before implementation started | `.specs/features/<feature>/contract.md` |
| Lessons already learned here (read before proposing anything) | `.specs/LESSONS.md` |
| Why the harness is shaped this way | `docs/harness-engineering.md` |
| Security posture | `docs/security.md` |

## Getting oriented

```
python scripts/bootstrap_context.py
```

Prints the current feature, phase, open tasks, recent commits, and uncommitted files. Run it
first, every session. It is cheaper than reading the repo.
