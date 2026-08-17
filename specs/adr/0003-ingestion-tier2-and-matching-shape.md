# ADR 0003: Ingestion (tiers 1-3) and matching technical shape

- **Status:** accepted
- **Date:** 2026-08-17

## Context

Slice 3 of `specs/features/001-cv-writer.md` (criteria 7-16) needs to fetch a job posting,
extract its text, extract structured requirements from that text, and produce a deterministic
match report against the profile. ADR 0002 deliberately deferred the ingestion/browser choices
to this slice. Four small library decisions need pinning down before code, per the spec's own
"technical shape decided before code, recorded as an ADR" convention.

## Decisions

- **Tier 1 HTTP fetch: stdlib `urllib.request`, not `requests`/`httpx`.** Tier 1 is one GET with
  a timeout and a User-Agent header — `urllib` covers that with zero new runtime dependencies.
  The fetch function takes an injectable `http_get` callable so tests never touch the network
  (per the criterion→test-placement table: "tier 1 with a stubbed HTTP layer"); the concrete
  library behind the default implementation is an internal detail the tests don't depend on. If
  a later slice needs retries/cookies/redirects that `urllib` makes painful, revisit then.
- **Main-text extraction: a small stdlib `html.parser.HTMLParser` subclass, not
  `readability-lxml`/`trafilatura`/`beautifulsoup4`.** Criterion 7 asks for "the main text",
  not a general-purpose readability algorithm — a boilerplate-tag blocklist (`script`, `style`,
  `nav`, `header`, `footer`, `aside`, `form`, `noscript`) plus visible-text concatenation is
  deterministic, dependency-free, and testable against fixture HTML. Revisit if real postings
  turn out to need smarter main-content detection than "strip the obvious chrome."
- **Requirement extraction (criterion 12): curated dictionaries + regex phrase matching, no
  NLP/LLM.** Matches ADR 0002's framing and the spec's own open question 4 (extraction may
  graduate to LLM-assisted later, but starts deterministic). Four dictionaries — skills,
  seniority signals, languages, work-model/location terms — each phrase match keeps the
  matched substring as `source_phrase` (criterion 12's "verbatim source phrase").
- **Tier 2 browser: Playwright, driving Chromium.** The spec names "the same Chromium already
  needed for PDF rendering" (criterion 9.2) — Playwright is the actively maintained Python
  binding with first-class `wait_for_load_state("networkidle")`, scroll-into-view, and locator
  APIs needed for cookie-banner dismissal and lazy-load triggering. Verified installable in this
  environment (`pip install playwright` + `playwright install chromium`, ~150MB one-time
  download) before committing to it. Selenium was the other candidate; Playwright's async-free
  sync API and built-in auto-waiting needs less boilerplate for the same behaviour.
  Tier 2 tests run against a local `http.server`-based fixture site (own thread, random free
  port) serving pages that exercise cookie banners / lazy content / a simulated block response —
  never a live site, per the criterion→test-placement table and criterion 10's no-evasion
  boundary (a live-site test would itself be the kind of automated traffic criterion 10 rules
  out for anything but a human-readable, consenting fetch).
- **Matching (criteria 13-16): plain functions over `Profile`/`RequirementSet`, no new
  dependency.** Scoring formula, evidence ranking, and gap detection are pure Python — this is
  the "deterministic, inspectable heart" the spec calls out, and pulling in a fuzzy-matching or
  ML library would work against criterion 14 (identical input -> identical report) for no proven
  benefit at this scale (a few dozen skills/requirements).

## Consequences

- New runtime dependency: `playwright` (plus its one-time Chromium download, done via
  `playwright install chromium` — not part of `pip install`, so CI/dev setup docs must call it
  out explicitly). No other new runtime dependencies this slice.
- Tier 1 and requirement extraction stay dependency-free and fast; only tier 2 pays the
  Chromium cost, and only when tier 1 actually fails or under-extracts (criterion 9's
  escalation order).
- The main-text extractor and requirement dictionaries are hand-rolled and will need real
  postings thrown at them to find gaps — flagged as a "watch this" for the first few real runs,
  same posture as ADR 0002 took with the PT-PT checker's ceiling (spec open question 5).
