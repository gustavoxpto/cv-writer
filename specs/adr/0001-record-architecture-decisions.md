# ADR 0001: Record architecture decisions

- **Status:** accepted
- **Date:** 2026-08-17

## Context

This repo is the reusable core of an AI-powered dev harness, built around peer programming, XP,
TDD, and spec-driven development, for a beginner learning software engineering by building.
Decisions about structure, security, and integrations need a durable, dated record — both so
future-you understands *why*, and so AI collaborators don't silently relitigate settled
questions.

## Decision

We use ADRs (this folder, numbered sequentially, immutable once accepted — supersede with a new
ADR rather than editing history) for structural/architectural/security decisions, and
`specs/features/` for feature-level specs. ADRs answer "why did we set it up this way";
feature specs answer "what should this feature do."

## Decisions recorded so far

- Secrets: encrypted-at-rest + ephemeral decryption only, no plaintext at rest. See
  `docs/security.md`.
- Deletion: never without fresh explicit human permission, in this repo and every repo derived
  from it. Hard rule, not a preference.
- VCS/CI: GitHub, Actions, CODEOWNERS, PR reviews.
- Approval gate: spec sign-off required before implementation, PR review required before merge
  — chosen deliberately over a lighter-weight gate, because the point of this harness is
  learning the *why*, not just shipping fast.

## Consequences

- Slower than "just let the AI merge to main" — that's the intended trade-off for a
  build-to-learn project.
- Requires actually writing specs before coding, which is friction early on but is the point.
