# Spec: CV Writer

- **Status:** signed-off
- **Author:** human (Gustavo) + AI pairing session, 2026-08-17
- **Date:** 2026-08-17 (revised same day after human review — see "Revision log")

## Why

Applying for jobs well is slow, and applying for jobs fast is usually done badly. A generic CV
gets filtered out; a genuinely tailored CV takes an hour of rereading the posting, digging up
which past achievement is relevant, and rewriting bullets to speak the posting's language. The
result is a bad trade: either few good applications or many weak ones.

The problem this solves, for one specific person (the maintainer, applying internationally):
**turn "a job posting" into "a truthful, well-matched, well-written CV" in minutes instead of an
hour — without inventing anything.** Two things make that possible:

1. Experience and skills stop being re-derived from memory for every application. They live once,
   in structured form, as reusable evidence (job histories written as STAR stories with numbers
   attached) that can be cross-referenced and selected per posting.
2. The tailoring decision becomes explicit and inspectable — *these* skills matched, *these* are
   gaps, *this* evidence was chosen and why — rather than an unexplainable blob of LLM output.

There is also an application-history problem: after 40 applications nobody remembers which CV
version went to which company, in which country, for which department. A track record of every
CV sent, queryable by date/company/country/area/skills, makes the next application cheaper than
the last and makes follow-ups possible at all.

**Learning goals** (this is a build-to-learn repo — the *why* behind the shape matters as much as
the feature): separating a pure domain core from an I/O shell, keeping an LLM in a bounded role
so the system stays testable, modelling data before writing code, and treating "the model must not
fabricate" as an engineering requirement with a test, not a hope.

## What (acceptance criteria)

Numbered and testable. Every test in `tests/` must cite one of these numbers.

### A. Profile: the single source of truth for real experience

1. A human-editable `data/profile.yaml` holds identity, contact fields, skills, languages,
   education, and job histories. Loading it produces a validated in-memory profile object;
   loading a file that violates the schema fails with an error naming the offending field and
   path, and never yields a partially-loaded profile.
2. Every job history entry has a stable `id`, company, role title, country, area/department,
   start date, and end date (or `present`), plus a list of achievement bullets.
3. Each job history has **between 3 and 5 achievement bullets**, and each bullet is stored as
   explicit STAR fields (`situation`, `task`, `action`, `result`). A history with fewer than 3 or
   more than 5 bullets fails validation.
4. **Each job history carries at least one quantified metric** across its bullets — value, unit,
   and direction/baseline where applicable (e.g. `+37%`, `R$1.2M`, `from 9 days to 2 days`),
   stored as structured data on the bullet whose `result` it belongs to. Individual bullets may be
   qualitative; a *history* with no metric anywhere fails validation, with a message naming the
   history. A `profile check` additionally reports (without failing) any history where only one of
   several bullets is quantified, since more proof is better.

   *Why this shape:* forcing a number onto every bullet invites invented precision — exactly the
   failure mode criterion 17 exists to stop. Per-history is the level at which "this role has
   proof" is a real claim.
5. Skills are first-class records (name, category, optional level, optional years) and are
   **linked to the job histories that evidence them**. A skill claimed with no evidencing history
   is loaded but reported by a `profile check` as unevidenced.
6. The validated profile is loaded into the embedded database so skills and histories can be
   queried and cross-referenced (e.g. "every bullet evidencing Python", "all histories in
   Portugal"). The database copy of the profile is **derived and rebuildable** from
   `data/profile.yaml`; re-running the load is idempotent and does not duplicate rows.

### B. Job posting ingestion

7. A posting can be ingested from a public URL: the tool fetches it, extracts the main text, and
   stores a raw text snapshot together with the source URL and fetch timestamp.
8. A posting can be ingested by pasting raw text instead, with company/role/country entered by
   the user. Pasted and fetched postings are otherwise indistinguishable downstream.
9. Ingestion escalates through three tiers before giving up, and the tier used is recorded with
   the posting:
   1. **Plain HTTP fetch** + main-text extraction (fast path, criterion 7).
   2. **Browser render** — when tier 1 returns non-200, times out, yields a JS-only shell, or
      extracts less than a configurable minimum of text, the posting is re-fetched in a real
      headless browser (the same Chromium already needed for PDF rendering): load the page, wait
      for network idle, scroll to trigger lazy-loaded content, dismiss cookie/consent banners by
      their standard accept controls, expand "see more" toggles, then read the *rendered* visible
      text — deliberately slower and unhurried rather than hammering the site.
    3. **Paste fallback** (criterion 8), offered with the reason tier 2 failed.
10. Tier 2 is a rendering strategy, not an evasion strategy: it operates only on pages a signed-out
    human could read in their own browser. It must not attempt logins, solve or bypass CAPTCHAs or
    anti-bot challenges, ignore a site's explicit blocking response, or issue rapid repeat
    requests. If a page answers with a challenge, a login wall, or an explicit block, tier 2 stops
    and hands over to tier 3 with that reason reported.
11. The tool never silently proceeds with empty or truncated posting text: below the minimum
    extraction threshold it always reports what happened and which tier produced it.
12. From posting text the tool extracts a structured requirement set: required skills, preferred
    skills, seniority signals, language(s), and location/work model — each requirement retaining
    the verbatim source phrase it came from.

### C. Matching (deterministic, inspectable)

13. Given a profile and a posting requirement set, the tool produces a **match report**:
    per-requirement status of `matched` / `partial` / `missing`, the profile skill or history that
    satisfies it, and an overall match score with the formula documented in the report.
14. The match report is deterministic: the same profile and posting text always produce an
    identical report, with no LLM call involved in producing it.
15. The report lists gaps explicitly (missing and partial requirements) so the human can decide to
    supply extra input, or to not apply at all.
16. For each requirement the tool ranks candidate evidence bullets by relevance and recency, and
    selects the bullets to feature, respecting the length budget of criterion 24.

### D. CV generation, language, and the anti-fabrication guarantee

17. Per application, the user may supply extra input (a cover note angle, an achievement not yet
    in the profile, emphasis instructions). Extra input is recorded with that application, and
    the user is prompted to promote reusable additions into `data/profile.yaml`.
18. The LLM's role is bounded to **rephrasing and ordering** selected evidence for the posting's
    language and emphasis. Every generated bullet carries the `id` of the profile bullet (or the
    per-application input) it was derived from.
19. A validator rejects a generated CV that contains (a) a bullet with no source `id`, (b) an
    employer, title, date, or credential absent from the profile, or (c) a numeric claim whose
    value is not present in its source bullet's metrics. Rejection names the offending line.
20. **The CV is written in the posting's language.** The language is detected from the posting
    text, shown to the user, and overridable before generation. Generation is refused for a
    language not listed in the profile's `languages` at working proficiency — the tool does not
    produce a CV in a language the maintainer cannot speak in the interview.
21. **European Portuguese (PT-PT) is a distinct target from Brazilian Portuguese.** When the
    output language resolves to PT-PT, the CV must follow European Portuguese orthography,
    grammar, and vocabulary, and a deterministic checker flags `brasileirismos` before the CV is
    accepted: BR-only lexis (e.g. *celular* → *telemóvel*, *time* → *equipa*, *arquivo* →
    *ficheiro*, *tela* → *ecrã*, *gerenciar* → *gerir*, *planejamento* → *planeamento*), the
    BR progressive *estar + gerúndio* where PT-PT takes *estar a + infinitivo*, BR clitic
    placement, and BR-preferred spellings under the orthographic agreement. The checker is a
    versioned, data-driven term/pattern list — extendable without touching code — reports the
    offending line and its PT-PT replacement, and blocks acceptance until resolved. PT-BR remains
    a valid target when the posting is Brazilian.
22. The LLM call sits behind one interface that tests replace with a recorded/fake responder, so
    the whole pipeline is testable offline with no API key and no network.
23. The tool never writes an `ANTHROPIC_API_KEY` (or any credential) to disk, to the database, or
    into a generated artifact; the key is read from the environment at call time only, per
    `docs/security.md`.

### E. Output

24. **One page is the target; two pages are the exception, and the human decides.** The tool aims
    to fit one page, and when the posting's requirements genuinely exceed that it proposes two
    pages, showing exactly what a one-page version would drop. The user picks one or two pages and
    the choice is recorded with the application. Page count is never silently changed to make
    content fit.
25. Each generated CV is written as Markdown — the versionable, diffable source — and rendered to
    a PDF through a single consistent visual template.
26. The PDF template obeys these rules, verifiable by inspecting the rendered document:
    - **Black text on white**, no colour fills, no shading, no coloured accents; hierarchy comes
      from size, weight, and spacing alone. (Also survives being printed or photocopied by a
      recruiter, and never fails a contrast check.)
    - **ATS-safe structure:** single column, no text boxes, no tables or multi-column layout used
      for positioning, no headers/footers carrying content, no icons or images conveying
      information, no text inside graphics, a small number of clearly-labelled,
      consistently-named sections (illustrative English example: Experience, Education, Skills —
      the actual wording follows the document's output language; see spec 003, criterion 26
      amendment), real bullet characters, and dates in a single consistent machine-readable
      format.
    - **Fonts:** one widely available, screen-and-print legible family from a documented
      shortlist (e.g. Arial/Helvetica, Georgia, Calibri, Verdana, Times New Roman), embedded in
      the PDF, at a minimum body size of 10pt — no decorative, condensed, or exotic faces, and no
      webfont that may fail to load at render time.
    - **Selectable, extractable text:** the rendered PDF's extracted text must match the Markdown
      source's content, which is the actual test for all of the above.
27. A plain-text variant is produced for job boards that reject PDFs, carrying the same content
    with no layout-dependent formatting.
28. Output paths are deterministic and collision-free per application (date + company + role
    slug), and generating twice for the same application produces a new version rather than
    overwriting a previous artifact.

### F. Track record database

29. Every generated application is persisted in the embedded SQLite database with: date, company,
    country, area/department, role title, source URL or `pasted`, ingestion tier used, match
    score, output language, page count, skills featured, paths to the Markdown/PDF/text artifacts,
    and the profile-bullet ids used.
30. The track record can be listed, sorted, and filtered by **date, company, country,
    area/department, and skill** — including combined filters (e.g. skill = Python AND country =
    Portugal, sorted by date descending).
31. The database file lives outside version control (it holds personal data), its location is
    configurable, and a fresh run against a missing database creates and migrates it without
    manual steps.

### G. Web UI

32. A local web UI is the primary interface: paste-or-URL a posting, review the match report and
    the gap list, add per-application input, confirm language and page count, generate, then
    download the Markdown/PDF/text.
33. The UI also browses the track record with the sorting and filtering of criterion 30.
34. All domain logic (profile, matching, generation, persistence) lives in importable modules with
    no web-framework imports; the UI layer only calls into them. Tests for A–F never start a web
    server.
35. The UI binds to localhost by default and is single-user; it ships no authentication and must
    not be exposed publicly in this version (see Out of scope).

### H. Repo hygiene (this feature makes the harness real)

36. `.github/workflows/ci.yml`'s placeholder step is replaced by the real dependency install,
    lint, and test commands, and CI passes on the PR implementing this spec.
37. `tests/` mirrors `src/`, with unit tests for A/C/D-validators, integration tests for the
    database and posting ingestion, and at least one e2e test walking posting → match → generated
    CV → track-record row using the fake LLM responder.

### Criterion → test placement

| Criteria | Where the tests live |
|---|---|
| 1–6 | `tests/unit/` (schema, STAR, per-history metric validation) + `tests/integration/` (profile load into DB, idempotency) |
| 7–12 | `tests/integration/` — tier 1 with a stubbed HTTP layer, tier 2 against local fixture pages served on localhost (never live sites in CI), tier-escalation and refusal cases (10) |
| 13–16 | `tests/unit/` — pure functions, no I/O |
| 17–23 | `tests/unit/` (validator, source-id tracing, PT-PT checker as a table-driven test) + `tests/integration/` (pipeline with fake LLM) |
| 24–28 | `tests/integration/` — render to a temp dir; PDF asserted by extracting its text and checking embedded fonts |
| 29–31 | `tests/integration/` (real SQLite in a temp file) |
| 32–35 | `tests/e2e/` (UI happy path) + one unit test asserting no web imports in the core |
| 36–37 | CI itself |

## Technical shape (chosen in this session, to be recorded as an ADR before code)

- **Python 3.12**, domain core as plain modules + Pydantic models; **FastAPI + Jinja2** server-
  rendered UI (chosen over a CLI because the tool should feel usable by a non-technical audience
  when demonstrated, and because it can later grow into something hosted).
- **SQLite** as the embedded database, in a file outside git; schema migrations kept as ordered
  SQL scripts under `src/`.
- **pytest** for tests, **ruff** for lint — both wired into CI (criterion 36).
- Markdown → HTML (Jinja print template) → **PDF via headless Chromium** rather than a native GTK
  toolchain, because the maintainer's environment is Windows and print CSS is easier to iterate on
  than a PDF drawing API. The same browser serves ingestion tier 2 (criterion 9), which makes one
  heavy dependency pay for two features — this strengthens the case against WeasyPrint noted in
  open question 2.
- Claude API behind a single `Rephraser` interface; fake implementation used in all tests.

## Delivery slices (TDD order — each slice is red → green → refactor, tests first)

1. **Profile core** — criteria 1–5. No DB, no UI, no LLM. Ends with a valid `profile.yaml`.
2. **Database + track record** — criteria 6, 29–31. Persistence and querying, still headless.
3. **Ingestion + matching** — criteria 7–16. Tier 1 and tier 3 first; tier 2 (browser) last in the
   slice, since it brings the browser dependency in. The deterministic, inspectable heart.
4. **Generation + guardrails + output** — criteria 17–28. LLM introduced last, and only behind the
   validators that can reject it. The PT-PT checker (21) is written before the LLM is called at
   all — it is a pure function over text and needs no model to test.
5. **Web UI + CI** — criteria 32–37.

Slices 1–2 are worth their own PR before anything LLM-shaped exists.

## Out of scope

- Cover letters, LinkedIn profile rewriting, outreach messages, interview prep.
- Multi-user, authentication, hosting, or any public deployment. Localhost single-user only. The
  "scale it later" ambition is served by criterion 34 (a UI-independent core), not by building
  multi-tenancy now.
- Automatic form-filling or auto-submitting applications to job boards or ATS systems.
- Parsing existing CV PDFs/DOCX into the profile, and LinkedIn data-export import. The profile is
  hand-authored (seeded by rereading old CVs) — parsing is unreliable and would be a feature of
  its own.
- DOCX output.
- Postings behind a login, and anything requiring a CAPTCHA/anti-bot challenge to be defeated or a
  site's block response to be worked around (criterion 10). Public, signed-out-readable pages
  only, with the paste fallback as the answer to everything else.
- Machine translation into a language the maintainer does not speak (criterion 20 refuses it), and
  any locale beyond PT-PT / PT-BR / EN getting dedicated grammar checking in this version.
- Multiple visual CV templates, or per-application design changes. One template, one look
  (criterion 26).
- Any claim of ATS "score" or beating a specific vendor's parser. Criterion 26 is about avoiding
  known-bad formatting, not reverse-engineering an ATS.
- Application-outcome tracking (interview / rejected / offer) and follow-up reminders — see open
  question 1.

## Open questions

Tracked, not blocking sign-off.

1. **Outcome tracking.** Out of scope above, but the track record is its natural home. Add a
   nullable `status` column now (cheap, no workflow) or keep the schema clean until the feature is
   specced?
2. **PDF renderer.** Headless Chromium is a heavy dependency, now justified twice (PDF + ingestion
   tier 2). Still worth a WeasyPrint spike on Windows during slice 4 before committing — ADR-worthy.
3. **Two stores, one truth.** `data/profile.yaml` is authoritative and the database copy derived
   (criterion 6). Editing the profile through the UI would break that. Keep YAML as the only write
   path for now?
4. **Skill extraction quality.** Requirement extraction (criterion 12) starts as a curated skill
   dictionary plus phrase matching. When it misses obvious requirements, does it graduate to an LLM
   extraction step that is then human-confirmed — keeping criterion 14's determinism for *scoring*
   while relaxing it for *extraction*?
5. **PT-PT checker's ceiling.** A term/pattern list catches lexis and common constructions, not
   register or idiom. Is a native-speaker read of the first few PT-PT CVs the acceptance test for
   whether the list needs to grow (and should those reads feed back into the list as fixtures)?
6. **Personal data.** The profile and database hold real contact details and employment history.
   `.gitignore` must cover `data/` (criterion 31), and `data/profile.example.yaml` — with fake data
   — becomes the committed reference. Confirm nothing real ever gets committed.

### Revision log

- **2026-08-17, after human review.** Metrics moved from per-bullet to per-history (criterion 4).
  Fetch failure now escalates to a browser render before the paste fallback, with an explicit
  no-evasion boundary (criteria 9–11). PDF formatting rules made concrete: B&W, ATS-safe
  structure, documented font shortlist (criterion 26). Two questions from the first draft were
  resolved and promoted into acceptance criteria: output language follows the posting with PT-PT
  treated as distinct from PT-BR (criteria 20–21), and one page is the target with a two-page
  option the human chooses (criterion 24). Criteria renumbered from 31 to 37; no tests existed yet
  to re-point.

- **2026-08-22, amending criterion 26 (spec 003).** Criterion 26's ATS-safe-structure bullet
  reworded, not deleted (hard rule #1): the parenthetical "standard section headings
  (Experience, Education, Skills)" — the superseded wording, quoted verbatim here — read as a
  mandate for those literal English words regardless of output language. It now reads as an
  illustrative English example of the underlying ATS-safe pattern: a small number of
  clearly-labelled, consistently-named sections. Prompted by
  `.specs/features/003-full-document-language-localization/spec.md` (AC-005), which found the
  original wording contradicted a non-English CV using translated section headings, which spec
  003 requires (criterion 26 itself still stands; only its ATS-safe-structure bullet changed).

## Sign-off

- [x] Human has read this and understands the *why*, not just the *what*.
- [x] Acceptance criteria are specific enough to write failing tests from.

Signed off by Gustavo (human), 2026-08-17, after the revisions in the log above.

*(Implementation does not start until this box is checked.)*
