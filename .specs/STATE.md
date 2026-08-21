# STATE

Working memory for this repository. **Read this first, every session.** It is the answer to
"what was happening here and where did it stop", so no session has to rebuild that from the diff.

`## Decisions` is append-only — never rewrite or remove an entry, even a superseded one; mark it
superseded and add the new one. `## Current` and `## Handoff` are snapshots and get overwritten.

---

## Current

- **Feature:** 003-full-document-language-localization
- **Phase:** design
- **Spec status:** signed-off (Gustavo, 2026-08-21, re-signed after migration)
- **Branch:** `spec/003-full-document-language-localization`

<!--
Phase is one of: idle | specify | design | tasks | contract | execute | validate | review
The PreToolUse hook on src/** reads Feature from here and refuses edits unless that feature's
spec.md is signed-off. Update this block when you move phase — it is not inferred.
-->

---

## Decisions

Lightweight decisions live here as `AD-NNN`. Anything hard to reverse gets a full ADR in
`specs/adr/` instead, and is linked from here rather than duplicated.

- **AD-001** (2026-08-20) — `.specs/` is the layout for all new features. `specs/features/001-cv-writer.md`
  stays frozen where it is as a historical record rather than being migrated; it is signed off,
  implemented across five merged PRs, and cross-linked from six `docs/pr/*` files, five ADRs and
  six pairing notes. The churn of moving it outweighs the consistency gained.
- **AD-002** (2026-08-20) — `specs/adr/` remains the home for heavyweight architecture decisions.
  `.specs/STATE.md` holds only the light ones. One decision, one home — never both.
- **AD-003** (2026-08-20) — Mission separation is implemented with Claude Code subagents, not
  separate OS processes. Separate processes are not available in this harness; subagents give
  separate context windows, separate system prompts and separate missions, which is the part
  that actually defends against mission capture. Revisit if a real orchestrator layer ships.
- **AD-004** (2026-08-20) — Blocking hooks over warning hooks. A warning that can be ignored is
  feed-forward wearing a sensor's clothes. Every blocking hook prints its own bypass instructions
  and logs the bypass below, so the escape hatch stays honest.
- **AD-004** (2026-08-21) — Spec 003 was migrated into `.specs/` and re-expressed in EARS rather
  than implemented from its 2026-08-19 form. The old form uses prose criteria 1-6 in the legacy
  `specs/` layout, which `validate_spec.py` cannot parse and the `src/**` hook cannot recognise as
  signed off, so implementing from it would have meant bypassing both gates on the first feature
  after the harness proved itself. The original file stays on branch
  `feat/003-full-document-language-localization` as the historical record — same treatment AD-001
  gives spec 001, and no deletion. Sign-off restarts because the criterion IDs are new; the
  substantive decisions from 2026-08-19, including OQ-1, carry over unchanged.

---

## Handoff









Snapshot of where work stopped. Overwrite freely — this is not a log.
Regenerate with `python scripts/handoff.py`.

- **Feature:** `002-requirement-dictionary-expansion` · phase `review`
- **Branch:** `feat/harness-engineering`
- **Last commit:** 1ba7e31 docs(002): record validation iteration 3 — PASS
- **Next step:** Spec 002 is PASS and complete; open a PR for feat/harness-engineering (needs Gustavo's go-ahead — outward-facing). Then spec 003: migrate specs/features/003-full-document-language-localization.md into .specs/ with EARS AC-NNN criteria before any code.
- **Blockers:** None for 002. For 003: its spec predates the harness — old specs/ layout, prose criteria 1-6, no AC-NNN IDs, so validate_spec.py cannot read it and the src/** hook will not recognise it as signed off.
- **Uncommitted:** 1 file(s) — pairing/sessions/2026-08-21-spec-002-first-full-loop.md

---

## Bypass log

Every time a blocking hook is overridden with `HARNESS_BYPASS=1`, a line lands here. An empty
section is the healthy state; a long one means a gate is miscalibrated and should be fixed rather
than routed around.

<!-- bypass-log -->
