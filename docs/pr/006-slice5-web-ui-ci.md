# PR body — CV Writer slice 5: web UI + CI (001, criteria 32-37)

Branch: `feat/001-slice5-web-ui-ci` → `main`.
Title: `feat(001): slice 5 — web UI + CI (criteria 32-37)`.

---

## What & why

Implements slice 5 of [`specs/features/001-cv-writer.md`](../../specs/features/001-cv-writer.md) —
the last slice: a localhost-only FastAPI + Jinja2 web UI walking posting → match report → extra
input → language + page-count confirmation → generate → download, plus a track-record browser
(criteria 32-33). All domain logic stays free of web-framework imports, mechanically enforced by
an AST-walking test rather than trusted by convention (criterion 34). This slice also closes the
CI gap slices 3-4 deliberately deferred: `main` has been CI-red since slice 3 because
`playwright install chromium` was never wired into the workflow — that's fixed here, and CI now
runs the whole suite, `tests/e2e/` included (criteria 36-37).

Nine design decisions were pinned down in an ADR, signed off by the human, before any code —
[`specs/adr/0005-web-ui-shape.md`](../../specs/adr/0005-web-ui-shape.md).

## What's in it

- **`src/cv_writer/web/`** (new subpackage):
  - `drafts.py` — `DraftStore`, an in-memory dict of `draft_id -> Draft` keyed by a `uuid4`.
    The `MatchReport` is deliberately never stored — it's re-derived on every page load from
    `extract_requirements()` + `build_match_report()`, both pure and deterministic (criterion
    14), so there is never a second, driftable copy of a value criterion 6 already treats as
    derived-only for the profile. Restarting the server loses in-progress drafts; finished
    applications are in SQLite from the moment `/drafts/{id}/confirm` succeeds and are
    unaffected.
  - `app.py` — `create_app()`, an injectable factory: `profile_path`, `db_path`, `output_dir`,
    `rephraser`, and `ingest_url` are all overridable, so the whole UI runs offline behind
    `FakeRephraser()` and a stub `ingest_url` — the same dependency-injection posture the rest
    of this codebase already uses everywhere (there is not one `unittest.mock` in this repo).
  - `routes.py` — every route the spec names: `/` (new application), `/drafts` (URL ingestion),
    `/drafts/paste` (paste fallback), `/drafts/{id}` (match report + gaps + extra-input form +
    language), `/drafts/{id}/inputs` (append extra input), `/drafts/{id}/generate` (run
    `generate_cv()`, measure page fit on success), `/drafts/{id}/pages` (the one-page-vs-two
    choice, showing exactly what gets dropped), `/drafts/{id}/confirm` (write artifacts, persist
    the application), `/applications` (track record, criterion 33), `/applications/{id}` (result
    + download links), `/applications/{id}/download/{kind}` (guarded file serving). Every
    handler is a plain `def`, never `async def` — Playwright's synchronous API (used by tier-2
    ingestion and PDF rendering) raises at runtime inside a running asyncio event loop, and
    Starlette runs `def` routes in a worker threadpool instead.
  - `__main__.py` — `python -m cv_writer.web`; binds `127.0.0.1:8000` by default, no `--host`
    flag, no auth/CORS/session middleware (criterion 35).
  - `templates/*.html.jinja` — five screens (new application, draft/match report, page choice,
    track record, application detail), rendered through their own `Jinja2` `Environment` with
    `"jinja"` added to `select_autoescape()`'s enabled extensions explicitly (FastAPI's
    `Jinja2Templates` default only recognises `.html`/`.htm`/`.xml`, which would have silently
    left every `*.html.jinja` template unescaped).
- **`src/cv_writer/generation/write_output.py`** (new) — `write_artifacts()`, the module that
  finally writes the three generated files (Markdown, plain text, PDF) to disk. Nothing in
  `generation/` wrote a file before this slice; `render_pdf_fn` is injectable so the unit test
  runs without Chromium.
- **`src/cv_writer/db/track_record.py`** gains `get_application(conn, id)` — a small, additive
  read function `insert_application()` had no counterpart for; the result page and the guarded
  download route both need to look up one application by id.
- **`tests/unit/web/`** (new): the AST-based no-web-imports guard (criterion 34), `DraftStore`,
  localhost binding + no CORS/auth/session middleware (criterion 35), and the download-route
  path-traversal guard (criterion 32 / ADR decision 7).
- **`tests/e2e/`** (was empty, now populated): `test_ui_happy_path.py` — the full walk criterion
  37 names, posting → match → extra input → generate → download → a real track-record row, plus
  a generation-failure case rendered through the UI; `test_ui_track_record.py` — combined
  filters and sort order (criterion 33), including "an unwhitelisted `sort_by` renders an error,
  not a 500"; `test_ui_ingestion_failure.py` — tier 1/2 failure offers the paste fallback with
  the reason, then paste succeeds (criteria 9.3, 11).
- **`.github/workflows/ci.yml`** — adds `playwright install chromium --with-deps` and changes
  the test step from `pytest tests/unit tests/integration -q` to `pytest tests -q`, so
  `tests/e2e/` actually runs in CI (criterion 36's acceptance evidence).
- **ADR 0005** records all nine decisions (web/ subpackage + AST-enforced import boundary, sync
  route handlers, in-memory draft store, injectable `create_app()`, two Jinja environments,
  `write_output.py`'s placement, the download path guard, localhost-only binding, CI's Chromium
  step) before any code was written.
- **New runtime dependencies**: `fastapi`, `uvicorn[standard]`, `python-multipart`; dev-only
  `httpx` (for `fastapi.testclient.TestClient`).
- **71 new tests** (full suite: 189 → 260), `ruff check` clean.

## Acceptance criteria covered

Criteria 32-35 (spec section G): the full UI walk (posting → match report/gaps → extra input →
language + page-count confirmation → generate → download), the track-record browser with
criterion 30's filters/sorting, the domain-core-has-no-web-imports boundary enforced by an AST
test, and localhost-only binding with no authentication. Criteria 36-37 (spec section H): CI
installs Chromium and runs the entire suite including a real e2e walk with `FakeRephraser`;
`tests/` mirrors `src/` with unit tests for the web-layer invariants and integration/e2e tests
for the flows that need real I/O.

## Manual verification

Started the real server (`python -m cv_writer.web`), confirmed via `netstat` it listens only on
`127.0.0.1:8000` (not `0.0.0.0`), hit `/` and `/applications` with `curl` (200 on both), then
stopped it. The full happy path (paste → match report → extra input → generate → page choice →
confirm → download all three artifacts → filtered track-record listing) was also walked by hand
against a `TestClient` script before the e2e tests were written, to shake out wiring bugs early —
none of the reported findings below came from that script; it just made writing the tests faster.

## Checklist

- [x] Spec in `specs/features/` signed off before implementation — `001-cv-writer.md`,
      criteria 32-37 targeted
- [x] ADR written before code, and signed off by the human before this exec pass started —
      `specs/adr/0005-web-ui-shape.md`
- [x] Tests written before/alongside implementation, every test citing its criterion
- [x] Local checks passing — `ruff check src tests` clean, `pytest tests -q` green (260 passed,
      up from 189)
- [x] No secrets committed — `ANTHROPIC_API_KEY` is never read, rendered, or persisted by the
      web layer; `ClaudeRephraser` (unchanged from slice 4) still reads it from the environment
      only inside `rephrase()`, and the default `create_app()` collaborator is that same
      `ClaudeRephraser` with no key handling added around it
- [x] Pairing notes added — `pairing/sessions/2026-08-18-slice5-web-ui-ci.md`
- [ ] Code-review pass — not run as part of this exec pass; per the plan this PR is picked up by
      a separate review pass before a human merges (see the plan's "agent chain" section)

### Reviewer: worth a look

1. **Company/country/area/role-title are collected upfront on both the URL and paste forms**,
   rather than only for paste (as criterion 8 literally describes) with the URL flow trying to
   guess them from the fetched page. `Posting.company`/`role_title`/`country` are optional and
   frequently `None` for a real fetched posting, and `Draft` needs all four confirmed before a
   match report or an `Application` can be built — asking upfront avoids an extra "confirm these
   fields" step the ADR's route table doesn't name. Worth confirming this reads naturally against
   a real posting URL, not just the fixture data these tests use.
2. **Page-fit measurement (`/drafts/{id}/generate`) and the final artifact write
   (`/drafts/{id}/confirm`) each do a real Chromium render.** For the common case (evidence
   already fits one page) that's two PDF renders per application, which is fine at this tool's
   stated single-user, occasional-use scale, but would be the first thing to optimise if that
   scale assumption ever changes.
3. **`get_application()`'s addition to `db/track_record.py`** wasn't spelled out in ADR 0005 line
   by line — it's a small, additive, no-schema-change read function that the result page and the
   guarded download route both needed and `insert_application()` had no counterpart for. Flagging
   it explicitly since "the ADR is the design" is this repo's stated posture and this is the one
   place implementation needed something the ADR didn't literally name.
4. **`generation/templates/*.jinja` (the print template, from slice 4) still isn't listed in
   `pyproject.toml`'s `package-data`** — only `db/migrations/*.sql` was, until this slice added
   `web/templates/*.jinja` alongside it. Both packages currently work under the editable install
   this repo's CI and dev setup use, so it's latent rather than active, but worth a follow-up fix
   so a real (non-editable) install doesn't quietly ship without its print template.
5. **The sort-order control in `templates/applications.html.jinja`** was built as a `<select>`
   (`descending=true|false`) rather than a checkbox specifically because an unchecked HTML
   checkbox omits its field entirely on submit, which would have silently frozen the sort order
   at "descending" no matter what the user picked. Called out in case a future template edit
   reintroduces a checkbox here without noticing why it was avoided.
