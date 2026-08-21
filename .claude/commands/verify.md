---
description: Validate phase — independent verifier walks the contract, checks evidence, runs a discrimination sensor, writes validation.md
argument-hint: <NNN-slug>
model: sonnet
---

Run the **Validate** phase for: **$ARGUMENTS**

Dispatch the `verifier` subagent — **fresh**, with no inherited context from whoever wrote the
code. Author ≠ verifier (`CLAUDE.md` hard rule #5); that separation is the only reason this gate
means anything.

Give it: `spec.md`, `contract.md`, the git diff for the feature, and the test files in scope.

It performs, in order: the contract walk, spec-anchored coverage (evidence or zero), assertion
depth, the discrimination sensor **in an isolated scratch copy — never `git stash`, never the
real tree**, and `python scripts/gate.py build`. Then it writes
`.specs/features/<slug>/validation.md` with a score per check against its stated minimum.

When it returns:

1. Run `python scripts/validate_state.py <slug>` yourself. It checks the checker: a report full
   of placeholders, a criterion with no `file:line`, or a PASS verdict sitting above a failed
   score row all exit non-zero.
2. **On PASS** — set `- **Phase:** review` in `.specs/STATE.md`, then `/pair-note` and `/pr`.
3. **On FAIL** — route the ranked gaps back to `implementer` as fix tasks, then re-dispatch the
   verifier. **Bounded to 3 iterations.** After the third, stop and escalate to the user with
   what is still failing; do not keep looping.

A **spec-precision gap** is not an implementation failure. It means the spec never stated a
precise outcome, so send it to `/spec`, not to the implementer — and do not let anyone close it
by loosening an assertion.
