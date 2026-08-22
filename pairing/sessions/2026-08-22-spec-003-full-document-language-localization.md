# 2026-08-22 — Spec 003 full-document language localization, contract fix through validation

## Goal

Execute spec 003 end to end (Contract → Execute → Validate) after correcting two unsigned-contract defects found mid-loop, completing the language-localization half of the 2026-08-19 operational readiness run.

## Tried

**C-003 as written forbade the edit C-003 itself required.** The first contract-draft check for
the machine-readable `reason_code` ended with "confirm no existing call site that constructs
`LanguageResolution(...)` was edited to supply `reason_code`" — a prohibition. But AC-007 names
`reason_code` as a public field, and there is exactly one construction site (the return of
`resolve_output_language()`, `language.py:169` today). Leaving it alone means `reason_code` is
`None` on every refusal and the criterion cannot be discharged. The check was rewritten: the
field defaults to `None` so no *other* site would need changing; the single production site
supplies it on every return path; three isolated refusal tests pin three different members; no
hardcoded value passes all three.

**C-006's "non-empty heading" assertion could not distinguish whether rendering happened.**
The negative test (no English word in a non-English render) ran over the entire rendered
document, which carries profile-authored content verbatim — a user-entered English bullet or
skill name would have failed it for reasons unrelated to headings. The positive assertion alone
(heading word present) passed on the un-stripped Markdown, so stripping Markdown markers could
have been skipped and the test still green. The check was rewritten: the negative assertion
scoped to lines starting with `"## "`; the `render_plain_text()` test asserts *both* presence
of the bare word *and* absence of `"## " + heading` (the second half is what actually fails if
markers are not stripped). Mutation #5 in validation confirmed: disabling the marker-stripping
killed only the "marker absent" assertion, proving the "word present" half alone would have
passed against the broken code.

**Tasks written before contract signature meant three tasks described a rejected shape.** T-002's
fixture on an unsupported language (the design had put German-proficiency regression tests
somewhere; the unsigned contract wanted to move them preemptively) would pass at T-002 (with
reason code `NOT_IN_PROFILE`), then T-003 would land the `SUPPORTED_LANGUAGES` capability gate
and flip the same fixture to `UNSUPPORTED_LANGUAGE`, turning T-002's own tests red inside T-003's
commit. The tasks were re-synced to the signed contract before Execute started: T-001 (the
preemptive rearrangement) and T-002 (add the `reason_code` field) both now use German, which
passes the capability gate, so T-002's tests stay green when T-003 lands it.

## Decided

- **Contract -> Execute -> Validate is the real gate.** Spec 002's experience already taught that
  the spec + task list stop nothing — the verifier's scrutiny before code exists (hard rule #5),
  and the verifier's adversarial read after, are where gaps surface. This session started with
  two confirmed defects in the signed contract itself because the first-pass check did not read
  the spec's wording precisely enough (C-003 named the field but the check named what not to do).
  Re-signed contract, executed clean.
- **Isolation is decision-forcing.** T-002's refusal tests use German deliberately, so that when
  T-003 lands the capability gate they stay green — an *arrangement* that forces a decision: if
  you change the fixture to an unsupported language, the test flips red and you have to decide
  whether to move it or change the criterion. A fixture on an already-unsupported language would
  have been a silent trap.
- **The task list is derived, not a first draft.** T-002, T-006, T-007 all re-synced one line
  each after contract sign; the full list was re-validated against the signed contract before
  Execute started. The checklist stops unintended work slipping through, but only if it stays
  faithful to what was actually signed.

## Learned

**The contract serves two different people.** The verifier signs it to say "I have checked this
against the spec and it's coverage-complete and testable"; the implementer reads it to know the
acceptance test for each item. One defect in the verifier's wording (C-003's prohibition that
contradicts the criterion) is invisible until the implementer reads it as a task — at which point
the task is unsolvable. Re-reading the spec before Execute ran caught both C-003 and C-006 from
context, but a contract written with full spec-precision from the start would not have needed a
re-read.

**A four-task group on one module (T-001 through T-005 on `language.py` logic) is self-stabilizing.**
T-001's rearrangement landed separately, so code review can see it as a clean prep step, not a
fix bundled into the commit that broke the test. T-002 + T-003 landed the model shape before the
code that returns it, in a deliberate order. T-004 + T-005 parametrize the new language across
the two gates. Each task left the gate green; when T-003 landed and touched behaviour that T-001's
fixture exercised, the gate caught it — but the test itself was already moved and stayed green by
design.

**Deletion without permission is structural, not about trust.** An implementer agent deleted
`rm -f` a scratch file it had created (untracked, not load-bearing), and self-reported the hard
rule #1 breach. A later agent, told explicitly not to delete, correctly left a stray probe file
(`_scratch_probe.txt`) in place and asked instead. The difference: the `Write` tool was blocked for
subagents by a worktree-isolation guard, so both did file edits through Bash. The first agent's
choice to use `rm` was conscious; the second agent's choice to ask was also conscious. The
contrast in outcomes is the rule working as designed — not about whether to trust the agent, but
about making the constraint explicit and visible to the executor (a human) to make the approval
decision.

## Links

- Spec: `.specs/features/003-full-document-language-localization/spec.md`
- Contract (signed after re-check): `.specs/features/003-full-document-language-localization/contract.md`
- Tasks (re-synced before Execute): `.specs/features/003-full-document-language-localization/tasks.md`
- Validation (PASS, iteration 1): `.specs/features/003-full-document-language-localization/validation.md`
- Commits: `4e37006..667f220` (13 task + 2 non-task commits; the first two were contract-sync and
  task-sync, neither containing code)
- Lesson added: L-008 (test positive + negative assertion pair for transformation verification)
