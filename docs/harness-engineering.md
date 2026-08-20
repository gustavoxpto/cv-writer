# Harness engineering

Why this repo's AI harness is shaped the way it is, what changed on 2026-08-20, and what was
deliberately left alone.

---

## 1. The idea

A **model** is the LLM. The **harness** is everything else around it: the instructions, the repo
structure, the linters, the tests, the progress files, the bootstrap scripts. The model is a
capable engineer on their first day; the harness is their onboarding. Drop a brilliant engineer
into a repo with no README, no documented architecture, no CI and no tests, and they will do
foolish things — not from incompetence, but from having no context.

The claim worth taking seriously: **the bottleneck is no longer the model's intelligence, it is
the quality of the environment it operates in.**

The framing comes from control engineering. There are two ways to control a system:

- **Feed-forward** — instructions given *before* execution to raise the chance of success.
  Preventive. Here: the spec, `CLAUDE.md`, `AGENTS.md`, architecture rules, the skill.
- **Feedback** — observing the result *after* execution and correcting what came out wrong.
  Here: linters, tests, type checks, the verifier agent.

A car's GPS does both. Feed-forward is the route it plots before you leave; feedback is
recalculating when you miss an exit. With only the route you are lost at the first mistake. With
only recalculation you set off with no direction at all.

**A spec is pure feed-forward.** It says what to do. It never verifies it was done. That is
enough to ship features. It is not enough to ship systems.

Two more pillars follow from how sessions actually work:

- **Memory** — state that survives a session ending, so the next one does not reconstruct it.
- **Bootstrap** — the mechanism that hands a fresh session that state cheaply.

---

## 2. What this repo looked like before

Documentation-driven, not tooling-driven. Zero slash commands, zero subagents, zero skills, zero
hooks; `.claude/` held only permission lists. Every process step — spec → red → green → refactor
→ pair note → PR → review — lived in prose in `CLAUDE.md` and held for exactly as long as an
agent remembered it. No model routing anywhere.

The Opus-plans-then-implements chain described in
`pairing/sessions/2026-08-18-slice5-web-ui-ci.md` had genuinely happened — but only in the
operator's head. Nothing in the repo encoded it, so nothing reproduced it.

Mapping the six known failure modes against that starting point:

| # | Failure mode | Covered before? |
|---|---|---|
| 1 | **One-shot hero** — attempts the whole app, blows the context window mid-run | Yes — delivery slices |
| 2 | **Premature victory** — declares done while lost in a large context | Yes — numbered acceptance criteria |
| 3 | **Amnesia between sessions** — a new session burns half its tokens rebuilding state | **No** |
| 4 | **Done without really testing** — defines what to test but never enforces it | **No** — nothing forced `pytest` before a commit |
| 5 | **Single process, self-judgement** — the agent that built it decides it is good | **No** |
| 6 | **Accumulated slop** — lose 5–20% quality per feature; compounds catastrophically | **No** |

Spec-driven development had bought failure modes 1 and 2. Half the harness. This change buys the
other half.

---

## 3. Change ledger

### 3.1 `.specs/` becomes the working memory — *memory pillar, failure mode 3*

**What.** New directory: `STATE.md` (`## Current`, append-only `## Decisions` as `AD-NNN`,
rewritable `## Handoff`, `## Bypass log`), `LESSONS.md`, `templates/`, and per-feature
directories holding `spec.md`, `design.md`, `tasks.md`, `contract.md`, `validation.md`.

**Why sound.** A spec records what to do; nothing recorded what *was* done, what went wrong, or
where work stopped. That gap is why a fresh session opens by reading the diff and guessing.
Splitting the append-only decision log from the rewritable handoff matters: decisions must
accumulate (a superseded one is still evidence of reasoning), snapshots must not.

**How.** Lazy creation — a file exists only once its phase produced content, so the absence of
`design.md` *is* the signal that Design was correctly skipped. `LESSONS.md` was seeded with five
real lessons mined from existing pairing notes and the handoff doc, not invented.

**Not done, on purpose.** Spec 001 was not migrated. It is signed off, implemented across five
merged PRs, and cross-linked from six `docs/pr/*` files, five ADRs and six pairing notes; the
churn outweighs the consistency. It stays frozen with pointers at both ends. Recorded as
`AD-001`. `specs/adr/` remains the home for heavyweight decisions — one decision, one home.

### 3.2 The contract phase — *failure mode 5, and the loop-termination problem*

**What.** A sixth phase between Tasks and Execute. The implementer writes `contract.md` — the
explicit list of observable outcomes it will deliver, each with the exact **Check** the verifier
will run. The verifier reviews that list against the spec and signs it **before any code is
written**. At validation time the verifier walks that exact list, item by item.

**Why sound.** It solves two problems with one artifact.

1. Nothing slips. The verifier is not scanning a diff for what might be missing; it is walking
   an agreed checklist.
2. The loop terminates. Without an agreed list, a verifier starts proposing unrelated
   improvements and the implementer chases them forever. The contract bounds the conversation:
   anything the verifier wants that is not on it goes back to Specify as a new criterion, not
   into this iteration as a gap.

This is the single most valuable idea taken from the source video, and it is **not** in the TLC
Spec-Driven skill.

**How.** `.specs/templates/contract.md`, `scripts/validate_contract.py`, `/contract`. The
validator checks every criterion is promised, nothing is promised that the spec did not ask for,
every item has a decidable **Check**, and the signature box is ticked before Execute.

### 3.3 `scripts/` — the sensors — *failure modes 4 and 6*

**What.** Eight stdlib-only sensors, each exiting 0 or non-zero, each unit-tested.

| Script | Rejects |
|---|---|
| `gate.py {quick,full,build}` | the single gate — ruff + tests, and at `build`, the artifact validators |
| `validate_spec.py` | criteria with no `SHALL`, placeholders, duplicate IDs, sign-off claimed with an unticked box or an open blocking question |
| `validate_tasks.py` | a task tracing to no criterion, a criterion no task covers, an unknown gate level, a missing "Done when" |
| `validate_contract.py` | an unpromised criterion, an item with no decidable check, an item citing a criterion that does not exist |
| `validate_state.py` | a criterion with no `file:line`, a PASS above a failed score row, a score row never run, a report still full of template text |
| `check_commit.py` | anything that is not a Conventional Commit |
| `test_census.py` | a drop in the test count |
| `bootstrap_context.py` | — (prints state) |

**Why sound.** The governing principle: *what enforces is not the instruction, it is the sensor.*
An agent must not be the judge of its own work; the judge must be a tool returning 0 or 1,
because an agent asked to evaluate its own code will read it and decide it is good enough
without running anything. That became **hard rule #4** in `CLAUDE.md`.

`test_census.py` deserves its own note. The opening scene of the failure this whole harness is
built against includes *"it overwrote a test, it deleted a test, it declared everything done."*
The cheapest way to turn a red gate green is to remove what is red. The census is a ratchet: the
count may rise freely, and a drop halts until a human accepts a new baseline with `--accept`.

**How.** `scripts/harness_lib.py` holds the markdown parsers as pure functions over text, so
every rule is unit-testable without touching the filesystem. 66 new tests in
`tests/unit/scripts/`, each one a deliberately injected fault: a criterion with no `SHALL`, a
task tracing to nothing, a validation report claiming PASS on a failed row. A validator that
passes those is decoration, not a sensor.

That paid for itself during construction — `test_only_commits_are_inspected` caught that the
commit-guard regex missed `git -C <path> commit`, a real hole through which any commit could
have walked past the gate. The hook was fixed, not the test.

### 3.4 Hooks — the gates that actually bite — *the whole point*

**What.** Five hooks in `.claude/settings.json`.

| Hook | Fires on | Behaviour |
|---|---|---|
| `session_start.py` | session opens | prints current feature, phase, open tasks, recent commits, dirty files into context |
| `pre_edit_src.py` | Edit/Write under `src/` | **blocks** unless `.specs/STATE.md` names a feature whose `spec.md` is signed off |
| `pre_commit.py` | any `git commit` | **blocks** on a malformed message or a red `gate.py quick` |
| `post_test_edit.py` | Edit/Write under `tests/` | **blocks** if the test count dropped |
| `on_stop.py` | turn ends | nudges if the tree is dirty and `STATE.md` was not touched |

**Why sound.** A warning an agent can ignore is feed-forward wearing a sensor's clothes.
`CLAUDE.md` hard rule #3 — spec before code — was prose for the whole life of this repo, which
means it held exactly as long as it was remembered. `pre_edit_src.py` makes it structural.

`on_stop.py` deliberately does **not** block: a Stop hook that refuses to let a session end can
trap it in a loop, and a memory nudge is not worth that risk. Recorded as a design choice, not
an oversight.

**How, and the escape hatch.** Every blocking hook prints its own bypass instructions.
`HARNESS_BYPASS=1` prefixed to a command, or a `.specs/BYPASS` file for tool calls that carry no
command string (Edit/Write). Each bypass appends a line to `.specs/STATE.md`. **Bypassing is
allowed; bypassing silently is not.** A long bypass log means a gate is miscalibrated and should
be fixed rather than routed around — that is the signal the log exists to produce.

`pre_edit_src.py` guards `src/` only. Tests, specs, docs and scripts stay freely editable,
because the failing test must be writable before the code exists.

### 3.5 Mission separation — *failure mode 5*

**What.** Seven subagents in `.claude/agents/`, each with one narrow mission and a `model:` tier.
`implementer` has no route to write `validation.md`; `verifier` has no `Edit` or `Write` tool at
all for `src/` or `tests/`.

**Why sound.** When you give an agent a mission it will do almost anything to accomplish it. Give
it a mission to *implement* and it will do everything to consider itself finished — including
deleting a test. Give it a mission to *validate* and it will do everything to validate. The
defence is not better instructions; it is that the agent holding the checklist never wrote the
code. That became **hard rule #5**.

**What was not adopted, and why.** The source argues for separate OS *processes* — an
orchestrator spawning implementer and validator in genuinely separate windows — noting that
leaked Claude Code source shows an orchestration layer being instrumented above agents. That is
not available here. Subagents do give separate context windows, separate system prompts and
separate missions, which is the part that actually defends against mission capture. Recorded as
`AD-003`; revisit if a real orchestrator layer ships.

### 3.6 Model routing

**Provenance, stated plainly: this did not come from the video.** The video never discusses model
tiering — it names models once, in passing. This section comes from the maintainer's own
requirement plus the *"Model Tier per Role"* table in the TLC Spec-Driven skill's
`references/sub-agents.md`, which is a real sourced authority on it.

| Work | Agent | Model | Reasoning |
|---|---|---|---|
| Orchestrating the loop | main session | `opus` | holds the whole state |
| Specify | `spec-author` | `opus` | maximum ambiguity; a vague criterion poisons every phase downstream |
| Design + ADRs | `architect` | `opus` | hard-to-reverse structural decisions outlive the feature |
| Task breakdown | `task-planner` | `sonnet` | structured judgement, shape already settled |
| Writing code | `implementer` | `sonnet` | ambiguity was resolved upstream |
| Validating code | `verifier` | `sonnet` | adversarial reasoning — never the cheapest tier |
| Settled-pattern scaffolding | `scaffolder` | `haiku` | no ambiguity left; applying a known shape |
| Session notes | `pair-scribe` | `haiku` | faithful summarisation of a transcript |

Two rules of thumb, adopted verbatim from the source:

- **When unsure, size up, not down.** An under-powered agent on ambiguous logic produces gaps the
  verifier then has to catch — more expensive than paying for reasoning once.
- **The verifier is never the cheapest tier.** A weak verifier defeats hard rule #5, and every
  gate downstream of it becomes a formality.

`scaffolder` is explicitly instructed that handing work back is the right answer, not a failure —
which is what keeps the cheap tier from becoming a false economy.

Advisory only. No gate, commit or verification step depends on the tier.

### 3.7 CI

**What.** `timeout-minutes: 20` on the job and `10` on the Playwright step; pip and
Playwright-browser caching; Python 3.10 → 3.12; a `test_census` step; and a new stdlib-only
`harness` job that validates every feature's artifacts on each PR.

**Why sound.** `docs/handoff-operational-readiness.md` records a run that wedged for **more than
five hours** on the Playwright install before being cancelled by hand. An unbounded step is not a
sensor, it is a hang — that became `L-005`. The version bump closes a gap where spec 001 targeted
3.12 while CI only ever proved 3.10. The `harness` job reports in seconds and tells a reviewer
whether the paperwork holds up before they read a line of code.

### 3.8 Feed-forward repairs

**What.** `CLAUDE.md` rewritten (four pillars, hard rules 4 and 5, a Commands block, the routing
table, the six-phase loop). New `AGENTS.md`. New `.claude/skills/spec-driven/SKILL.md` with the
auto-sizing table and EARS notation. Ten slash commands. `docs/architecture.md` rewritten from a
five-line placeholder. `README.md` Status section corrected. `.github/CODEOWNERS` pointed at the
real account.

**Why sound.** A stale guide is *negative* feed-forward: it actively misleads. `docs/architecture.md`
claimed the repo was an empty scaffold while `src/` held ~55 modules; `README.md` claimed there
was no git remote while five PRs had merged through one; `CODEOWNERS` requested review from
`@your-github-username`, which is nobody. Each of those cost real tokens and real trust every
time an agent read it.

The `CLAUDE.md` Commands block closes a smaller but constant leak: an agent previously had to
*infer* `.venv/Scripts/python.exe -m pytest`, and inferring it wrong is a wasted turn every
session.

`AGENTS.md` exists because it is the emerging cross-tool convention and it was named directly as
a feed-forward artifact. It is thin on purpose — it points at `CLAUDE.md` rather than
duplicating it, because two copies of a contract is one copy too many.

---

## 4. What was deliberately not adopted

| Not adopted | Why |
|---|---|
| Separate OS processes for implementer and validator | Not available in Claude Code. Subagents capture the mission-separation benefit. `AD-003` |
| Migrating spec 001 into `.specs/` | Signed off, implemented, cross-linked from 17 files. Churn outweighs consistency. `AD-001` |
| Installing `tlc-spec-driven` as a dependency | It assumes its own layout and ceremony, some of which conflicts with this repo's human-sign-off gate and build-to-learn framing. Its ideas were adopted; its files were not |
| A machine-owned `lessons.json` state file | Over-engineered for a single-maintainer repo. `LESSONS.md` in plain markdown is readable by both parties |
| Warning-only hooks | A warning that can be ignored is not a sensor. `AD-004` |
| Cleaning `.claude/settings.local.json` | ~60 accreted one-off allow entries, some malformed (`Bash(is None)`, `Bash(main)`). Cleaning means deleting lines — hard rule #1, needs explicit permission |
| Removing the stray root artifacts | `tmp_review_full_diff.txt` (185 KB) and `wc_diff_review_tmp.txt` (25 KB). Same reason. A `.gitignore` pattern is proposed instead |

---

## 5. Concept → artifact, with provenance

| Concept | Source | Artifact here |
|---|---|---|
| Feed-forward vs feedback | video, 4:20–5:35 | the four-pillar table in `CLAUDE.md` and `README.md` |
| Harness = everything around the model | video, ~1:05 | this document; the repo layout |
| Progress files hold state between sprints | video, 9:18–9:34 | `.specs/STATE.md`, `tasks.md` |
| Bootstrap scripts rebuild context | video, ~6:28 | `scripts/bootstrap_context.py` + `SessionStart` |
| The agent must not be the judge; the judge returns 0 or 1 | video, 6:55–7:25 | hard rule #4, `scripts/gate.py` |
| Force test execution at task end | video, 7:10–7:25 | `pre_commit.py` runs `gate.py quick` |
| Separate missions, separate agents | video, 7:25–8:15 | `.claude/agents/`, hard rule #5, `AD-003` |
| **Contract between implementer and tester** | video, 9:34–10:24 | `contract.md`, `validate_contract.py`, `/contract` |
| Tester walks the list item by item | video, 9:58–10:24 | the contract walk in `.claude/agents/verifier.md` |
| Bounded self-correction loop | video, 10:32–11:07 | `/verify`, 3 iterations then escalate |
| Scored evaluation with a stated minimum | video, 11:42–11:51 | the `## Score` table in `validation.md`; `validate_state.py` |
| Evaluation is pluggable (unit, integration, Playwright) | video, 11:51–12:01 | `gate.py` levels |
| Accumulated slop compounds | video, 8:15–8:40 | `gate.py build`, the CI `harness` job |
| EARS notation, requirement IDs | TLC `specify.md` | `.specs/templates/spec.md`, `validate_spec.py` |
| Gate contract by task level | TLC `implement.md` | the gate table in `tasks.md` |
| Author ≠ verifier, evidence-or-zero | TLC `sub-agents.md` | hard rule #5, `validate_state.py` |
| Discrimination sensor (mutation) | TLC `sub-agents.md` | `validation.md`, `.claude/agents/verifier.md` |
| Model tier per role | TLC `sub-agents.md` | the routing table in `CLAUDE.md` |
| Batch ~7 tasks per worker, never split a phase | TLC `sub-agents.md` | the delegation section of the skill |

---

## 6. Sources

- [Spec Driven chegou no limite — Harness Engineering é o próximo passo](https://www.youtube.com/watch?v=dLs-Pbn8stU) — Waldemar Neto, Dev Lab. Portuguese; translated and adapted.
- [tlc-spec-driven](https://agent-skills.techleads.club/skills/tlc-spec-driven/) — Tech Leads Club. [Source](https://github.com/tech-leads-club/agent-skills).
- [Harness Engineering: The Missing Layer in Specs-Driven AI Development](https://loiane.com/2026/04/harness-engineering-missing-layer-specs-driven-ai-development/) — Loiane Groner.
