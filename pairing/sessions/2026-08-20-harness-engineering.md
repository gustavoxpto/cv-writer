# 2026-08-20 — Harness engineering layer

## Goal

Compare this repo's harness against Waldemar Neto's *"Spec Driven chegou no limite — Harness
Engineering é o próximo passo"* and the Tech Leads Club `tlc-spec-driven` skill, and close the
gaps. Explicit extra requirement from Gustavo: route work to the right model tier — high
reasoning for planning and orchestration, mid for writing and reviewing code, fast for
deterministic repeats.

## Tried

**Getting the video's content.** The YouTube caption API returned HTTP 200 with a zero-length
body (the `pot` parameter is now required), so the transcript came out of the rendered
transcript panel via the browser tools instead. Worth knowing for next time: the caption endpoint
is no longer a shortcut.

**Reconciling two answers that conflicted.** Gustavo chose "harness + retrofit spec 002" for
scope and "adopt TLC's `.specs/` layout" for structure. Taken literally, full adoption means
moving spec 001 — which is signed off, implemented across five merged PRs, and cross-linked from
six `docs/pr/*` files, five ADRs and six pairing notes. That is the "full retrofit" he had just
declined. Rather than pick one silently, the conflict was named in the plan and resolved:
`.specs/` becomes the layout for everything new, spec 002 migrates as the live proof, spec 001
stays frozen with pointers at both ends. Recorded as `AD-001` so the reasoning outlives the
session.

**Model routing turned out not to be in the video at all.** It names models once in passing
("Claude, GPT-5, whatever") and never discusses tiering. Rather than dress up an invention as a
finding, the routing table was sourced to the TLC skill's `references/sub-agents.md` "Model Tier
per Role" table, and `docs/harness-engineering.md` says so explicitly.

**Two hook designs were rejected.** A `Stop` hook that *blocks* when the handoff is stale would
enforce memory hygiene — and could trap a session in a loop it cannot exit. It only prints.
Warning-only versions of the other hooks were also rejected (`AD-004`): a warning an agent can
ignore is feed-forward wearing a sensor's clothes.

**Heredocs kept failing.** Several multi-line `bash <<'EOF'` blocks containing markdown died with
"unexpected EOF". Switched to the Write tool for content and short Python files for bulk edits.

## Decided

Six changes, in `docs/harness-engineering.md` with full rationale. In short:

1. `.specs/` — `STATE.md` (append-only decisions + rewritable handoff), `LESSONS.md`, five
   templates, per-feature artifact directories. The memory pillar.
2. **The contract phase.** The implementer writes what it will build; the verifier signs it
   against the spec *before any code exists*; at validation the verifier walks that exact list.
   The highest-value idea from the video, and not in the TLC skill.
3. Eight sensors in `scripts/`, each exiting 0/1, each unit-tested.
4. Five hooks that actually block, each printing its own escape hatch, each bypass logged.
5. Seven subagents with mutually exclusive tool sets — `implementer` cannot write
   `validation.md`, `verifier` cannot touch `src/` or `tests/` — plus model tiers.
6. CI: a 20-minute timeout, caching, Python 3.12, and a stdlib-only `harness` job.

Two new hard rules in `CLAUDE.md`: **#4 the agent is never the judge** (a task is done when a
sensor exits 0), and **#5 author ≠ verifier**.

## Learned

**The sensors caught their own bugs, twice, which is the whole argument.**

`test_only_commits_are_inspected` failed on `git -C <path> commit`: the commit-guard regex
allowed `-flag` tokens between `git` and `commit` but not a flag *with an argument*. Any commit
issued as `git -C . commit` would have walked straight past the gate. The hook was fixed, not the
test — and the test is the only reason it was ever known.

Then spec 002 itself failed `validate_spec.py` on two criteria that plainly do contain `SHALL`.
The parser only read a list item's first line, so any criterion that wrapped lost its verb. That
one is worse than a bug: an unfixed version teaches people to write one-line criteria to keep the
validator quiet — the tool reshaping the work to suit itself. Fixed with `_item_text()`, plus a
regression test.

**A stale guide is negative feed-forward.** `docs/architecture.md` described an empty scaffold
while `src/` held ~55 modules; `README.md` said there was no git remote after five PRs had merged
through one; `CODEOWNERS` requested review from `@your-github-username`. Each one cost tokens and
trust every time an agent read it. Fixing them is not tidying — it is the cheapest quality work
available.

**Still fuzzy:** whether `PreToolUse` on `src/**` will feel like a guardrail or an obstacle in
daily use. The bypass log is the instrument for that — if it fills up, the gate is miscalibrated
and should be changed rather than routed around.

## Next

Spec 002 sits at `draft`, both sign-off boxes unticked. **The loop is correctly halted there** —
that is the new gate doing its job on its first real feature, not a failure to finish. Gustavo
reads `.specs/features/002-requirement-dictionary-expansion/spec.md`, resolves OQ-1 and OQ-2 if
he wants to (both non-blocking), ticks the boxes and sets `Status: signed-off`. Then `/tasks 002-…`
→ `/contract` → `/implement` → `/verify`.

Branch `feat/harness-engineering` is committed locally. Pushing and opening the PR are
outward-facing — Gustavo's call. Never merge; that is a human's job (`CLAUDE.md` hard rule #3).
