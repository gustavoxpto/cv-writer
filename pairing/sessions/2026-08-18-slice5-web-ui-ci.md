# 2026-08-18 — CV Writer slice 5: web UI + CI

## Goal

Deliver slice 5 of `specs/features/001-cv-writer.md` — the last slice: criteria 32-37, a
localhost-only FastAPI + Jinja2 UI over the domain core built in slices 1-4, plus the CI work
slices 3-4 deliberately deferred here. This session ran as the "exec" step of a planned agent
chain: an Opus session drafted and got sign-off on ADR 0005 in a prior window, and this session's
job was to implement the nine decisions in that ADR exactly as written — TDD through the
criteria, wire CI, write the PR doc and this note, then branch/commit/push/open-PR and stop
(never merge; that's a human's job, `CLAUDE.md` hard rule #3).

## Tried

- **Where does company/country/area/role-title get confirmed for a URL-fetched posting?** The
  ADR's route table lists `/drafts` (URL) and `/drafts/paste` (paste) but doesn't spell out
  exactly which form fields each carries. `Posting.company`/`role_title`/`country` are optional
  and usually `None` for a real fetched page, while `Draft` needs all four fields (plus `area`,
  which isn't on `Posting` at all) confirmed before a match report or an `Application` can be
  built. Considered adding an extra "confirm these fields" screen between ingestion and the match
  report. Went instead with collecting company/country/area/role-title upfront on *both* forms —
  the URL form asks for them alongside the URL, the same way the paste form already has to per
  criterion 8. Simpler (one less screen, one less route), and the user typically knows the
  company/role before they paste a URL anyway. Flagged in the PR's "reviewer: worth a look" since
  it doesn't match criterion 8's literal wording as closely as a "guess then confirm" flow would.
- **Where does page-fit measurement actually render from?** `fit_to_page_budget()` (slice 4) is
  pure and takes an injected `render_and_count` callable — the web layer had to supply a real one.
  First instinct was to reuse `write_output.py`'s `write_artifacts()` for the measurement pass
  too, but that writes three files (including the .md/.txt) for what should be a throwaway
  measurement. Wrote a small `_measure_page_count()` in `routes.py` instead: narrow the CV to a
  candidate `source_ids` list, render Markdown → HTML → a PDF in a `tempfile.TemporaryDirectory()`,
  read the page count back, and let the temp dir clean itself up. Keeps `write_artifacts()`'s job
  as "write the real, final files" and nothing else.
- **When does page-fit get computed — on `/generate` or on `/pages` GET?** ADR decision 3 says
  `Draft` carries the page-fit result "after generation," and the route table says
  `/drafts/{id}/generate`'s job includes "on success measure page fit and redirect." Read literally
  and implemented that way: `/generate` computes and stores `draft.page_fit` once, right after
  `generate_cv()` succeeds; `/pages` (GET) just reads it back, and `/confirm` (POST) reads it back
  again rather than recomputing. This also settled a smaller question for free: since `page_fit`
  is stored, `/confirm` doesn't need a second Chromium measurement pass to know which bullets
  belong to the "1 page" option — only the *final* artifact write (`write_artifacts()`) does a
  second real render, which is unavoidable since that's the actual deliverable file, not a
  measurement.
- **Autoescaping silently off — caught before it shipped, not after.** Built `routes.py`'s Jinja
  setup with FastAPI's `Jinja2Templates(directory=...)` shortcut first. Before writing any
  template content, checked what `jinja2.select_autoescape()`'s default `enabled_extensions` is —
  `("html", "htm", "xml")` — against the planned template filenames (`index.html.jinja`, etc.),
  which end in `.jinja`, not `.html`. That default would have silently served every template
  *unescaped*, meaning a posting's raw text (attacker- or just messily-formatted-controlled,
  in principle) could inject arbitrary HTML into a rendered page. `generation/render_html.py`
  had already hit this exact trap in slice 4 and fixed it by explicitly naming `"jinja"` in
  `enabled_extensions` — copied that fix here rather than rediscovering it via a failing test.
  Worth remembering as a pattern: any new Jinja environment in this repo needs that same explicit
  extension list, since the file-naming convention (`*.html.jinja`) doesn't match Jinja's own
  autoescape defaults.
- **Sort-order control: checkbox vs. select.** First draft of `applications.html.jinja` used a
  `<input type="checkbox" name="descending">` for ascending/descending. Caught during review-before-
  commit: an *unchecked* HTML checkbox doesn't submit its field at all, so unchecking "descending"
  and submitting would have silently kept the query param absent — which the route defaults to
  `True` — meaning the control could never actually select ascending order via a real form
  submission (only by hand-editing the URL, which is how the automated test caught nothing, since
  the test drives query params directly rather than the HTML form). Switched to a `<select>` with
  explicit `true`/`false` option values, which always submits something.

## Decided

- `src/cv_writer/web/{__init__,app,drafts,routes,__main__}.py` + `templates/*.html.jinja`:
  `create_app()` as an injectable factory (profile_path/db_path/output_dir/rephraser/ingest_url),
  `DraftStore` as a plain in-memory dict keyed by `uuid4` with the `MatchReport` deliberately
  never stored (re-derived from pure functions on every page load, matching criterion 14's
  determinism and criterion 6's "the profile's DB copy is derived, not a second source of truth"
  precedent extended to this new derived value). Every route handler is a plain `def` — Playwright's
  synchronous API (tier-2 ingestion, PDF rendering) raises inside a running asyncio event loop, so
  `async def` handlers were never on the table once that was checked against the actual libraries
  in use, not just against general FastAPI style advice. Downloads are guarded by re-resolving the
  stored path against the resolved output directory at request time (`Path.resolve()` +
  `is_relative_to`-equivalent parent check), not by trusting the slug function that built the path
  in the first place.
- `src/cv_writer/generation/write_output.py` (new): `write_artifacts()`, calling the existing
  `render_markdown`/`render_plain_text`/`render_html`/`render_pdf` and writing all three files.
  Placed in `generation/`, not `web/`, so criteria 25-28's actual output logic stays reachable by a
  plain unit/integration test rather than buried behind a web framework only an e2e test could
  exercise — matching criterion 34's spirit even though `write_output.py` itself has zero
  web-framework imports either way.
- `src/cv_writer/db/track_record.py` gains `get_application(conn, id)` — a small gap
  `insert_application()` left with no matching single-row read, needed by the result page and the
  download route. Additive only, no schema change, exported from `db/__init__.py` alongside the
  existing track-record functions.
- `.github/workflows/ci.yml`: `playwright install chromium --with-deps` between dependency
  install and lint; test step widened from `pytest tests/unit tests/integration -q` to
  `pytest tests -q` so `tests/e2e/` actually runs in CI — criterion 36's acceptance evidence, and
  the fix for the CI-red state that's held since slice 3 merged.
- ADR 0005 records all nine decisions before any of this code was written (already signed off by
  the human in a prior planning session; this session implemented it, didn't re-litigate it).
- 71 new tests (full suite: 189 → 260): `tests/unit/web/` (AST import-boundary guard, DraftStore,
  localhost/no-middleware, download-path-traversal guard), `tests/unit/generation/` +
  `tests/integration/generation/` (`write_artifacts()`, real-Chromium and fake-render variants),
  `tests/integration/db/` (`get_application()`), and `tests/e2e/` (was empty; now the full UI
  happy path, the track-record filter/sort UI, and the ingestion-failure-then-paste walk).

## Learned

- **Writing a throwaway `TestClient` smoke script *before* the formal e2e tests caught every real
  wiring bug in one pass** (a route referencing the wrong redirect location, a form field name
  mismatch, the autoescape gap above) with a much faster edit-run loop than iterating on
  `pytest` directly would have given, since the script prints exactly what each step returned
  instead of a full traceback per failure. The formal e2e tests then went green on the first
  real run — the script wasn't a replacement for the tests criterion 37 asks for, but writing one
  first paid for itself immediately. Worth doing again for any future slice that adds a new
  driven-end-to-end surface.
- **An ADR's route table can name *what* a route does without settling every question an
  implementer will actually hit** (see "Tried" above on company/country/area/role-title timing) —
  and that's fine as long as the gap gets a documented decision and a flag for review, not a
  silent choice. The instruction to "stop and report" if a decision looks wrong is for
  *disagreeing* with the ADR; filling in a genuinely unspecified detail in the ADR's own spirit is
  a different, much more common case, and doesn't need to block on a human before proceeding.
- **A destructive-by-omission bug (autoescape silently off) is just as worth catching before
  shipping as a destructive-by-commission one** — nothing in this repo's test suite would have
  caught unescaped template output without a test specifically checking for it, and no such test
  was written (an oversight worth naming, not hiding): the fix here came from checking the
  library's actual default behavior against the file-naming convention in use, before writing
  template content, rather than from a failing test. A follow-up worth considering: a small
  regression test asserting HTML metacharacters in posting text come back escaped in the rendered
  draft page.

## Next

This PR is picked up by a separate code-review pass (per the plan's agent chain) before a human
reviews and merges — this session does not merge, per `CLAUDE.md` hard rule #3 and its own
explicit authorization boundary (branch/commit/push/open-PR, then stop). See the PR doc's
"Reviewer: worth a look" section for the specific points flagged for that pass and for the human
review that follows it. With this slice, all seven criteria groups (A-H) in
`specs/features/001-cv-writer.md` are implemented; nothing is deferred to a slice 6.
