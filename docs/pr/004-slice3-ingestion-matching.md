# PR body — CV Writer slice 3: ingestion + matching (001, criteria 7-16)

Branch: `feat/001-slice3-ingestion-matching` → `main`.
Title: `feat(001): slice 3 — ingestion + matching (criteria 7-16)`.

---

## What & why

Implements slice 3 of [`specs/features/001-cv-writer.md`](../../specs/features/001-cv-writer.md): ingesting a job posting through three escalating tiers (criteria 7-11), extracting a structured requirement set from its text (criterion 12), and building a deterministic match report against the profile (criteria 13-16) — "the deterministic, inspectable heart" the spec calls out. Still no LLM, still no UI; those are slices 4-5.

## What's in it

- **`src/cv_writer/ingestion/`**
  - `models.py` — `Posting` (raw text, source, fetch timestamp, `ingestion_tier`, optional company/role/country), `IngestionFailure` (tier attempted + reason), `Requirement`/`RequirementSet` (criterion 12, each requirement keeps its verbatim `source_phrase`).
  - `text_extraction.py` — `extract_main_text()`: a stdlib `html.parser`-based boilerplate-tag blocklist + visible-text extractor, no new dependency (ADR 0003). Shares `BOILERPLATE_TAGS` and `collapse_whitespace()` with tier 2.
  - `fetch_tier1.py` — plain HTTP GET (stdlib `urllib`, injectable `http_get` for tests) + main-text extraction (criterion 7). Escalates on non-200, a request that never completes, or extracted text below a configurable minimum (criterion 9.1).
  - `fetch_tier2.py` — headless-browser render via Playwright + Chromium (criterion 9.2): detects an explicit block status or a CAPTCHA/login-wall phrase and stops immediately (criterion 10 — a rendering strategy, not an evasion one, one navigation, no retries, honest custom User-Agent), otherwise waits for network idle, dismisses a cookie banner, scrolls to trigger lazy content, expands "see more" toggles, strips boilerplate from the live DOM, reads visible text.
  - `fetch_tier3.py` — `ingest_pasted()`: paste fallback (criterion 8), no escalation, shapes pasted input into the same `Posting` model.
  - `pipeline.py` — `ingest_from_url()`: tier 1 → tier 2 escalation, tier recorded on success, both tiers' failure reasons reported on failure — never a silent or crashing result (criteria 9, 11).
  - `requirements.py` — `extract_requirements()`: four curated dictionaries (skills, seniority, languages, work-model/location) + regex phrase matching, with a required/preferred zone scan for skills.
- **`src/cv_writer/matching/`**
  - `models.py` — `MatchStatus`, `EvidenceBullet` (identified by `history_id`+`bullet_index` — `Bullet` still has no id of its own, the open point carried from slice 2), `RequirementMatch`, `MatchReport` (`.gaps()` for criterion 15).
  - `matcher.py` — `build_match_report(profile, requirement_set, reference_date=...)`: pure, deterministic (criterion 14), a documented weighted-score formula attached to every report (criterion 13).
  - `ranking.py` — `rank_evidence_bullets()` (relevance + recency, fully deterministic tie-break) and `select_bullets_within_budget()` — a first cut at criterion 16's "respecting the length budget of criterion 24" ahead of slice 4's real page-fit algorithm.
- **ADR 0003** records the tier-2/extraction/matching library choices (stdlib `urllib`, stdlib `html.parser`, curated dictionaries, Playwright + Chromium).
- **101 new/total tests**: `tests/integration/ingestion/` (tier 1 with a stubbed HTTP layer, tier 2 with 8 tests against a real local-fixture HTTP server via real Playwright — never a live site, escalation-policy tests with both tiers stubbed, requirement extraction) and `tests/unit/matching/` (pure-function tests with in-memory profiles, no file I/O).
- **`pyproject.toml`** — `playwright` added as a runtime dependency. Its Chromium binary is fetched separately via `playwright install chromium` (~150MB, not part of `pip install`) — **CI wiring for this is slice 5's job**, flagged here since this slice introduces the dependency but doesn't touch `.github/workflows/ci.yml`.

## Acceptance criteria covered

Criteria 7-11 (spec section B, ingestion): three-tier fetch/paste/escalate with tier recorded, no silent thin-text results. Criterion 12: structured requirement extraction with verbatim source phrases. Criteria 13-16 (spec section C, matching): deterministic match report, documented score formula, explicit gap list, relevance+recency-ranked evidence within a length budget.

## Review pass (before this PR)

Ran `/code-review` against the diff (three passes) before opening this PR and fixed everything real it found — a required/preferred zone-marker substring collision (`"Preferred Qualifications"` reverting to required mid-heading), inline-HTML text concatenation (`<span>Python</span><span>SQL</span>` → `"PythonSQL"`), a flat-counter (vs. stack) tag-skip bug in the tier-1 HTML parser with a proven tier-1→tier-2 recovery path, seniority years counting the *gap* between jobs as experience, word-boundary-vs-plain-substring false positives in both skill matching (`"sql"` matching `"PostgreSQL"`) and language matching (a generic `"Portuguese"` entry satisfying a `"European Portuguese"` requirement), an uncaught exception on a malformed URL, a `min_chars=0` edge case that could build an invalid `Posting`, tier 2 accepting non-block non-200 responses (e.g. a 404 page's filler text), and a block-signal check ordered *after* boilerplate DOM stripping (which could hide a block message rendered inside `<header>`/`<aside>`). Full rationale and the specific fix for each is in the pairing note's "Review pass" section, one regression test per fix (18 added, 83 → 101 total).

## Learning notes

- **"Deterministic" needed a `reference_date` escape hatch, not a compromise.** Seniority matching has to resolve `"present"` against *some* date — threading it as an overridable parameter (default `date.today()`) kept the function pure and testable without pretending time doesn't exist.
- **Two tiers can share a *policy* without sharing a *mechanism*.** Tier 1's stdlib HTML parser knows tags, not CSS; tier 2's rendered-DOM read knows visibility, not semantics. Both needed "boilerplate" to mean the same tag list, but tier 2 couldn't reuse tier 1's parsing *function* — only the tag list and the whitespace-normalization rule.
- **A three-pass code review before the first commit, not after, front-loaded the PR review.** All three passes independently found the same top bug; between them, real correctness issues (gap-counted experience years, substring-vs-word-boundary false positives) surfaced that none of the 83 tests written test-first had covered, because the tests were written to prove the intended behavior, not to hunt for where the implementation quietly diverged from it.

## Checklist

- [x] Spec in `specs/features/` signed off before implementation — `001-cv-writer.md`, criteria 7-16 targeted
- [x] Tests written before/alongside implementation, every test citing its criterion
- [x] CI passing — `ruff check` clean, `pytest` green locally (101 passed)
- [x] No secrets committed — no network calls in tests (tier 1 stubbed, tier 2 against a local fixture server only)
- [x] Pairing notes added — `pairing/sessions/2026-08-18-slice3-ingestion-matching.md`, including the pre-commit review pass

### Reviewer: worth a look

1. **`playwright install chromium` is not part of `pip install -e .`.** Anyone pulling this branch needs to run it once before tier 2's tests (or real ingestion) will work. Slice 5 needs to add it to `.github/workflows/ci.yml`.
2. **Location/work-model requirements always report `PARTIAL`, never matched/missing.** `Profile` has no structured work-model/relocation-preference field yet; a fabricated matched/missing verdict felt worse than an honest "can't confirm automatically." Worth confirming that's the right call, or whether `Profile` should grow a preferences field sooner.
3. **`EvidenceBullet` is still identified by `(history_id, bullet_index)`, not a stable bullet id** — the same open point slice 2's pairing note flagged, now touched by a second slice. Slice 4's anti-fabrication validator (criterion 19, "every generated bullet carries the id ... it was derived from") will need this resolved one way or another.
4. **Required/preferred skill zoning is a heuristic, not a parser** (`_skill_zones()` in `requirements.py`). It's been hardened against the one real collision the review pass found, but real postings will likely surface more edge cases — flagged in ADR 0003 as a "watch this" item, same posture as the PT-PT checker's ceiling in the original spec's open questions.
