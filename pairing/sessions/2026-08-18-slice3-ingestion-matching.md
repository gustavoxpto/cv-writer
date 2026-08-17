# 2026-08-18 — CV Writer slice 3: ingestion + matching

## Goal

Deliver slice 3 of `specs/features/001-cv-writer.md`: criteria 7-16 — fetch or paste a job
posting through three escalating tiers, extract a structured requirement set from its text, and
build a deterministic match report against the profile. Still no LLM, still no UI (per the
spec's slice ordering) — this is "the deterministic, inspectable heart."

## Tried

- **Main-text extraction library choice.** Considered `readability-lxml`/`trafilatura`/
  `beautifulsoup4` for tier 1's HTML-to-text step. Rejected in favor of a ~60-line
  `html.parser.HTMLParser` subclass (boilerplate-tag blocklist + visible-text concatenation) —
  criterion 7 asks for "the main text," not full readability heuristics, and a stdlib-only
  extractor is trivially deterministic and fixture-testable. Recorded as ADR 0003; flagged
  there as a "watch this against real postings" decision, not a permanent one.
- **Tier 2's text extraction: reuse the tier-1 HTMLParser vs. read the live DOM.** First pass
  fed `page.content()` (Playwright's serialized HTML) through the same `extract_main_text()`
  tier 1 uses, on the theory that "one extractor, two tiers" would be the cleanest shape. Backed
  out: after JS interaction, elements toggle `style="display:none"` on/off, and a stdlib HTML
  parser has no CSS engine — it can't tell a dismissed cookie banner from a collapsed one that
  still needs a click. Switched to removing boilerplate tags from the *live* DOM
  (`page.evaluate` + `querySelectorAll(...).remove()`) and letting `page.inner_text('body')`
  — which does respect visibility — read what's left. Same *policy* (the shared
  `BOILERPLATE_TAGS` set), different *mechanism*, because only the rendered engine can see
  which content is actually visible after cookie-dismiss/scroll/expand.
- **Cookie-banner/see-more detection: fixed CSS ids vs. text-based selectors.** Went with
  Playwright's `:has-text(...)` selectors ("Accept all", "Accept cookies", "See more", …) tried
  in a fixed order, plus one common vendor id (`#onetrust-accept-btn-handler`) rather than
  trying to enumerate every consent-management-platform's markup. This is exactly the kind of
  list ADR 0003 flags as needing real postings thrown at it to find gaps.
- **User-Agent for tier 2: spoof a real browser, or identify honestly?** Went with the same
  custom UA string tier 1 already sends (`cv-writer/0.1 (...)`). Criterion 10 explicitly frames
  tier 2 as "a rendering strategy, not an evasion strategy" — pretending not to be automated
  would work against that framing even though it might dodge more bot-detection in practice.
- **Required vs. preferred skill split (criterion 12).** Needs *some* section-awareness — the
  same word ("Kubernetes") means something different under "Requirements" vs. "Nice to have."
  Went with a lightweight zone scan: track section-marker offsets in the text, classify each
  matched skill phrase by the nearest marker before it, default to "required" until a preferred
  marker is ever seen. A real segmentation/section-parser would be more robust but is more
  machinery than a curated-dictionary extractor (spec open question 4) seems to warrant yet.

## Decided

- `src/cv_writer/ingestion/{models,text_extraction,fetch_tier1,fetch_tier2,fetch_tier3,
  pipeline,requirements}.py`:
  - `models.py` — `Posting` (raw text, source, fetched_at, `ingestion_tier`, optional
    company/role/country), `IngestionFailure` (tier_attempted + reason), `Requirement`/
    `RequirementSet` (criterion 12, each requirement keeps its verbatim `source_phrase`).
  - `text_extraction.py` — `extract_main_text()`, tier 1's pure HTML-to-text function.
  - `fetch_tier1.py` — `fetch_tier1(url, http_get=..., min_chars=...)`; `http_get` is
    injectable (tests never touch the network), default is a thin `urllib` wrapper. Escalates
    (returns `ok=False`) on non-200, a request that never completes, or text below `min_chars`.
  - `fetch_tier2.py` — `fetch_tier2(url, ...)`, real Playwright + Chromium: navigate, detect an
    explicit block status (401/403/429/503) or a CAPTCHA/login-wall phrase and stop, otherwise
    wait for network idle, dismiss a cookie banner, scroll to trigger lazy content, expand
    "see more" toggles, strip boilerplate from the live DOM, read visible text.
  - `fetch_tier3.py` — `ingest_pasted(text, company=, role_title=, country=)`, no escalation,
    just shapes pasted input into the same `Posting` model.
  - `pipeline.py` — `ingest_from_url()`: tries tier 1, escalates to tier 2 on any failure,
    returns a `Posting` (tier recorded) on success or an `IngestionFailure` naming both tiers'
    reasons on failure — never a silent empty result (criterion 11). Tier 3 is invoked directly
    by the caller, not from the pipeline, since it needs user-supplied fields the pipeline
    doesn't have.
  - `requirements.py` — `extract_requirements()`, four curated dictionaries (skills, seniority,
    languages, work-model/location) + regex phrase matching + the required/preferred zone scan
    described above.
- `src/cv_writer/matching/{models,matcher,ranking}.py` (criteria 13-16):
  - `models.py` — `MatchStatus`, `EvidenceBullet` (identified by `history_id` +
    `bullet_index`, since `Bullet` still has no id of its own — the slice-2 pairing note's open
    point remains open, now touched by a second slice), `RequirementMatch`, `MatchReport`
    (`.gaps()` for criterion 15).
  - `matcher.py` — `build_match_report(profile, requirement_set, reference_date=...)`: pure,
    deterministic (criterion 14), weighted score with the formula in `SCORE_FORMULA` and
    attached to every report (criterion 13). `reference_date` defaults to `date.today()` but is
    overridable — needed because seniority's years-of-experience math has to resolve `"present"`
    against *some* date, and tests pin it rather than depending on the wall clock.
  - `ranking.py` — `rank_evidence_bullets()` (relevance = skill-name mentions in the bullet's
    own STAR text, then recency, then a full deterministic tie-break) and
    `select_bullets_within_budget()` — a first cut at criterion 16's "respecting the length
    budget of criterion 24" (`DEFAULT_LENGTH_BUDGET_CHARS = 2200`, greedy selection across
    requirements in priority order, dedup'd, always keeps at least one bullet). Explicitly not
    the final page-fit algorithm — that's slice 4, measured against the real PDF template.
  - Location/work-model requirements always come back `PARTIAL` with an explanatory note:
    `Profile` has no structured preference field to check them against, and a fabricated
    matched/missing verdict would be worse than an honest "can't confirm automatically."
- ADR 0003 records the four library choices (stdlib `urllib`, stdlib `html.parser`, curated
  dictionaries, Playwright+Chromium) before code, per the repo's own convention.
- 45 new tests (22 ingestion integration incl. 4 real-Playwright-against-a-local-fixture-server
  tests for tier 2, 19 matching unit tests, plus the fixture-server + conftest scaffolding
  itself). Full suite: 83 passed, `ruff check` clean. `pyproject.toml` gained `playwright` as a
  runtime dependency; its Chromium binary was fetched once via `playwright install chromium`
  (~150MB, not part of `pip install` — CI will need this called out explicitly in slice 5).

## Review pass (before commit)

Ran `/code-review` against the diff (three passes, one asked for explicitly) before committing
— this repo's "review before merge" gate, applied here pre-commit rather than only at PR time.
All three passes independently reproduced the same top finding; between them they surfaced 10
real, fixed bugs plus a few cleanup/perf items. Fixed before commit, each with a regression
test:

- **`requirements.py` zone-marker overlap (found by all three passes).** "Qualifications" (a
  required-section marker) is a substring of "Preferred Qualifications" itself, so that very
  common heading planted a required-zone boundary a few characters after its own preferred-zone
  boundary, silently reclassifying everything under it as required. Fixed by dropping any
  required-marker match that falls inside a preferred marker's own matched span.
- **`matcher.py` experience-years counted the gap between jobs as experience.** Was
  `max(end_dates) - min(start_dates)` (the full span); two 1-year jobs eight years apart came
  out as ~10 years of experience. Fixed to merge overlapping/adjacent intervals and sum their
  actual durations — directly relevant given the codebase's anti-fabrication posture, even
  though this is matching (13-16), not the generation validator (19) that phrase is really
  about.
- **`matcher.py` fuzzy skill matching was plain substring, not word-boundary.** "sql" fuzzy-
  matched "PostgreSQL", "git" fuzzy-matched "GitHub Actions" — false partial credit for
  unrelated skills. Fixed by reusing `requirements.py`'s boundary regex (now exported as
  `word_boundary_pattern()`, cached, and shared by `matcher.py` and `ranking.py` too — three
  independent boundary-regex implementations collapsed into one).
- **`matcher.py` language matching cross-matched a generic entry against a specific variant.**
  A profile listing plain "Portuguese" satisfied a "European Portuguese" requirement, because
  "portuguese" is a substring of "european portuguese". Notable given the spec's own PT-PT/
  PT-BR distinction (criterion 21) — fixed by requiring an explicit variant marker
  ("european portuguese" / "pt-pt" / etc. in the profile's language name) for those two
  specific requirement values, leaving the generic substring match for everything else.
- **`text_extraction.py` merged adjacent inline elements with no separator.**
  `<span>Python</span><span>SQL</span>` (a common skill-pill pattern) extracted as "PythonSQL",
  silently dropping both from requirement extraction. Fixed by joining data chunks with a
  leading space and collapsing whitespace runs afterward (`collapse_whitespace()`, now also
  shared with tier 2 — see below).
- **`fetch_tier1.py` crashed instead of failing cleanly on a malformed URL.**
  `urllib.request.Request(url, ...)` was called *outside* the try/except, so a scheme-less URL
  raised an uncaught `ValueError` instead of the documented `HttpError` -> escalation path.
  Moved inside the try, `ValueError` added to the caught exception tuple.
  `fetch_tier1(min_chars=0)` had the same class of problem one level up: `len(text) < 0` is
  never true, so a fully empty extraction could report `ok=True` and build an invalid
  `Posting` downstream (`raw_text` requires `min_length=1`). Fixed with `max(min_chars, 1)`.
- **`fetch_tier2.py` only failed on 4 named block statuses, not any non-200.** A 404 (or any
  other non-200 outside {401,403,429,503}) fell through to full rendering and could return a
  dead page's boilerplate-stripped filler as if it were real posting content — inconsistent
  with tier 1's blanket "any non-200 fails". Fixed to fail on any non-200, keeping the specific
  "blocked: HTTP xxx" wording only for the named codes.
- **`fetch_tier2.py` stripped boilerplate tags before checking for a block/CAPTCHA message.**
  A block message rendered inside a `<header>` or `<aside>` (both boilerplate tags) would be
  silently discarded by the DOM cleanup before `_BLOCK_SIGNAL_PHRASES` ever saw it — the
  no-evasion check needs to see the block message wherever it renders. Reordered: block-check
  first, against the full text; boilerplate stripped only after.
- **`text_extraction.py`'s skip-tracking was a flat counter, not a stack.** A boilerplate tag
  closed by a mismatched end tag could desync the counter and swallow the rest of the page.
  Switched to a list-based stack (pop the matching entry, not just decrement); documented the
  residual limitation (a boilerplate tag *never* closed anywhere still isn't recoverable by a
  non-HTML5 parser) directly in the module docstring, with a test proving tier 1 -> tier 2
  escalation recovers from exactly that case rather than silently returning wrong output.
- **`fetch_tier3.py` didn't validate company/role_title/country non-blank**, despite the
  module's own docstring claiming they're "known immediately for a pasted posting." Added the
  same blank check the text already got.
- Cleanup, no behavior change: `select_bullets_within_budget()`'s docstring said "stop at the
  first bullet that doesn't fit" but the code actually skips it and keeps scanning smaller
  lower-priority ones (a better use of the budget) — docstring corrected to match; duplicate
  `histories_by_id` dict construction in `ranking.py` extracted to one `_histories_by_id()`
  helper; regex compilation in `requirements.py` now `@cache`d instead of recompiling per call.

18 new regression tests added alongside the fixes (101 total, up from 83; `ruff check` still
clean). One item considered and *not* changed: `fetch_tier3.ingest_pasted()` raises `ValueError`
on bad input rather than returning a typed `IngestionFailure` like the pipeline does — kept as
a deliberate difference (documented in the module's docstring) since tier 3 is a direct call
with caller-controlled arguments, not a description of an external fetch outcome.

**Process note, not a code finding:** one of the three review passes ran as a background
sub-agent and self-reported deleting an untracked scratch file (`_review_diff.txt`, its own
`git diff HEAD` export, created and removed within its own job) without asking — a violation of
this repo's hard "never delete without explicit permission" rule regardless of whose file it
was. Verified via `git log --diff-filter=A` that the file was never tracked and nothing of the
user's was lost, but flagging it here as the kind of thing that shouldn't happen unnoticed.

## Learned

- **"Deterministic" needed a small escape hatch, not a compromise.** Seniority matching has to
  answer "how many years is 'present' as of today," which is inherently time-dependent — not a
  contradiction of criterion 14 (no LLM, no randomness) so much as an orthogonal axis. Threading
  a `reference_date` parameter through (default `date.today()`, override in tests) kept the
  function pure and testable without pretending time doesn't exist.
- **A rendered page's "visible text" and "not-boilerplate text" are answered by two different
  engines, and conflating them cost a false start.** `html.parser` knows tags, not CSS;
  Playwright's `inner_text()` knows visibility, not semantics. Tier 2 needs both, so it borrows
  a *list* (`BOILERPLATE_TAGS`) from tier 1's module rather than a *function* — worth remembering
  next time two tiers seem like they should obviously share one implementation: sometimes they
  should only share the policy.
- **Open point for slice 4, logged rather than solved here (carried over from slice 2, now
  doubly relevant):** `EvidenceBullet` identifies a bullet by `(history_id, bullet_index)`
  because `Bullet` has no stable id. Slice 4's validator (criterion 19, "every generated bullet
  carries the id ... it was derived from") will need this resolved one way or another — either
  `(history_id, bullet_index)` becomes the canonical id shape everywhere, or `Bullet` grows a
  real `id` field (a `profile.yaml` schema change touching every fixture). Two slices now lean
  on the DB-rowid/positional-index workaround; that's a signal it's due, not a coincidence.

## Next

Slice 4 (criteria 17-28): per-application extra input, the bounded `Rephraser` LLM interface
(behind a fake for tests, criterion 22), the anti-fabrication validator (criterion 19) and the
PT-PT `brasileirismos` checker (criterion 21, written before the LLM is ever called since it's a
pure function over text), then Markdown -> PDF/plain-text output. Slice 5 will also need to add
`playwright install chromium --with-deps` to `.github/workflows/ci.yml` alongside the real
dependency/lint/test steps (criterion 36) — flagging now since this slice introduced the
dependency but doesn't touch CI itself, per the spec's own slice ordering.
