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

- **Feature:** `003-full-document-language-localization` · phase `design`
- **Branch:** `spec/003-full-document-language-localization`
- **Last commit:** c661577 docs(003): re-sign the spec with OQ-4 and OQ-5 resolved
- **Next step:** Spec 003 is signed off; next phase is Design — architect writes design.md plus an ADR (size large: spans language.py and render_text.py, adds a fourth language, amends signed spec 001). Rebase this branch onto main once PR #7 merges.
- **Blockers:** None. PR #7 (spec 002 + harness) is open with CI green, awaiting Gustavo's review and merge.
- **Uncommitted:** 0 file(s) — clean tree

---

## Bypass log

Every time a blocking hook is overridden with `HARNESS_BYPASS=1`, a line lands here. An empty
section is the healthy state; a long one means a gate is miscalibrated and should be fixed rather
than routed around.

<!-- bypass-log -->
