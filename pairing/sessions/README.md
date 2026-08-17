# Pairing session logs

One file per pairing session (human + AI, driver/navigator), named `YYYY-MM-DD-topic.md`. This
is the trail of *how* a decision was reached, not a changelog of *what* changed (git already
tracks that).

Suggested shape per entry:

```markdown
# 2026-08-17 — <topic>

## Goal
What we set out to do this session.

## Tried
What approaches were tried, including ones we backed out of.

## Decided
What we ended up doing, and why — link to the spec/ADR if one resulted.

## Learned
(Build-to-learn framing) — what concept clicked this session, what's still fuzzy.
```

This folder is the peer-programming half of the harness: it makes the "navigator" reasoning
visible instead of losing it once the PR is merged.
