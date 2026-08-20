---
description: Draft the PR body for a finished feature from its spec, tasks and validation report
argument-hint: <NNN-slug>
model: haiku
---

Draft the PR body for: **$ARGUMENTS**

Refuse if `python scripts/validate_state.py <slug>` does not exit 0. A PR for a feature that
never passed validation is a PR asking a human to do the verifier's job.

Dispatch the `scaffolder` subagent with `.github/pull_request_template.md`, the feature's
`spec.md`, `tasks.md` and `validation.md`, plus `docs/pr/006-slice5-web-ui-ci.md` as the house
style to match. Output goes to `docs/pr/NNN-<slug>.md`.

The body must carry:

- what changed and which criteria it satisfies, by ID
- the validation verdict, including the discrimination sensor result
- a **"Reviewer: worth a look"** section flagging the judgement calls — the places where a
  different decision was defensible. This is what makes the review a teaching checkpoint rather
  than a rubber stamp, and it is the part a template cannot generate for you.

**Then stop.** Opening the PR and pushing are outward-facing actions: confirm with the user
first. Never merge — that is a human's job (`CLAUDE.md` hard rule #3).
