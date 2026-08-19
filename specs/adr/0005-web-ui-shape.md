# ADR 0005: Web UI + CI shape

- **Status:** accepted
- **Date:** 2026-08-18

## Context

Slice 5 of `specs/features/001-cv-writer.md` (criteria 32-37) adds the first web surface and
closes the CI gap that has kept `main` red since slice 3. Nine decisions need pinning down
before code.

## Decisions

### 1. The web layer is `src/cv_writer/web/`, and criterion 34 is enforced by a test

A subpackage inside the distribution, not a sibling top-level package. Criterion 34 constrains
the *direction* of imports, not the directory: `web/` may import `profile`/`db`/`ingestion`/
`matching`/`generation`; none of those five may import `fastapi`/`starlette`/`uvicorn`/
`python-multipart`.

Enforced by `tests/unit/web/test_core_has_no_web_imports.py`, which walks each core module's AST
(`ast.parse` → `ast.Import` / `ast.ImportFrom`) and asserts no web-framework module is imported.
AST rather than grep: a grep hits the word inside a docstring or, worse, inside
`ingestion/requirements.py:36`, where `"fastapi": ["fastapi"]` is a legitimate *skill dictionary
entry* and would produce a permanent false positive.

**Rejected: trusting the convention without a test.** Criterion 34 is the criterion that keeps
this tool re-shellable later; slice 4 set the precedent of proving such a rule mechanically
("verified by grep, not just by convention" for `anthropic` imports).

**Consequences:** adding a web import to a core module fails a fast unit test with the offending
module and symbol named.

### 2. Route handlers are `def`, never `async def`

Every route is a plain synchronous function, so Starlette runs it in a worker threadpool.

This is not a style preference. `ingestion/fetch_tier2.py` and `generation/render_pdf.py` both
use **Playwright's synchronous API**, which raises at runtime when called from inside a running
asyncio event loop. An `async def` handler that calls `ingest_from_url()` or `render_pdf()`
fails with *"It looks like you are using Playwright Sync API inside the asyncio loop"*. `def`
handlers avoid this and additionally keep the blocking `urllib` fetch off the event loop.

**Rejected: converting the core to Playwright's async API.** It would push `async` into
`ingestion/` and `generation/` — colouring the domain core with a concern that belongs to the
shell, and forcing every existing test to become async for no gain.

**Consequences:** a module docstring on `web/routes.py` states the rule and the reason, so
nobody "modernises" it later. Concurrency is bounded by the threadpool, which is irrelevant at
criterion 35's single user.

### 3. Draft state lives in memory, keyed by a uuid4; the match report is re-derived

`web/drafts.py` holds a `DraftStore` — a module-level dict of `draft_id -> Draft`, where `Draft`
carries the `Posting`, the company/country/area/role the user confirmed, the accumulated
`list[ExtraInput]`, the language choice, and (after generation) the `GeneratedCv` and page-fit
result.

The `MatchReport` is deliberately **not** stored. Criterion 14 makes it deterministic and
LLM-free, so `extract_requirements()` + `build_match_report()` re-derive it on each page load
from pure functions. Storing it would create a second copy of a derived value — the same
mistake criterion 6 already forbids for the profile.

**Rejected: a `drafts` table in SQLite (migration 0003).** Drafts would survive a restart, but
transient half-finished state would then live in the same file criteria 29-31 define as the
*finished* track record, and it would need an expiry/cleanup story the spec never asked for.

**Rejected: round-tripping posting text through hidden form fields.** Stateless and
restart-proof, but posting bodies are large and the back button starts producing surprising
results.

**Consequences:** restarting the server loses in-progress drafts; finished applications are in
SQLite and unaffected. Documented in the module docstring in the same candid register
`generation/output_paths.py:4-12` already uses for its concurrency caveat.

### 4. `create_app()` is a factory taking its collaborators by injection

```python
def create_app(
    *,
    profile_path: Path | None = None,      # default: data/profile.yaml
    db_path: Path | None = None,           # default: db.connection.get_db_path()
    output_dir: Path | None = None,        # default: generation.output_paths.DEFAULT_OUTPUT_DIR
    rephraser: Rephraser | None = None,    # default: ClaudeRephraser()
    ingest_url: Callable[..., Posting | IngestionFailure] = ingest_from_url,
) -> FastAPI:
```

The whole suite runs offline with no API key by passing `FakeRephraser()` and a stub
`ingest_url`. This matches how the repo already fakes everything — dependency injection, never
`unittest.mock` (there is not one `MagicMock` or `patch` in the codebase, and `ingest_from_url`
itself already takes `http_get` and `tier2_fetcher` as parameters).

**Rejected: FastAPI's `Depends()` with dependency overrides.** It is the framework-native
answer, but it would express test seams in framework vocabulary, and criterion 22's "one
interface tests replace with a fake" is already satisfied by plain parameters.

### 5. Two Jinja environments, not one

`web/templates/*.html.jinja` gets its own `Jinja2Templates`, separate from the module-level
`Environment` in `generation/render_html.py`. They share a library, not a purpose: one renders a
**print** document destined for Chromium's PDF engine, the other renders **screens**.
Autoescaping is on in both.

### 6. `generation/write_output.py` writes the artifacts; the web layer does not

New pure-ish I/O module in the generation package:

```python
def write_artifacts(
    *,
    cv: GeneratedCv,
    profile: Profile,
    paths: OutputPaths,
    render_pdf_fn: Callable[[str, Path], Path] = render_pdf,
) -> WrittenArtifacts:   # markdown_path, pdf_path, text_path
```

It calls the existing `render_markdown` / `render_plain_text` / `render_html` / `render_pdf` and
writes the three files, creating the output directory. Nothing in the package writes `.md`/`.txt`
today — slice 4 left that to "the caller". Putting it in the web layer would bury real output
logic (criteria 25-28) behind a web framework where only an e2e test could reach it, against the
spirit of criterion 34. `render_pdf_fn` is injectable so the unit test runs without Chromium; the
integration test uses the real one.

### 7. Downloads are served from the DB-recorded path, re-validated against the output directory

`GET /applications/{id}/download/{kind}` (`kind` ∈ `markdown|pdf|text`) reads the stored
`markdown_path`/`pdf_path`/`text_path` off the `Application` row, resolves it, and serves it via
`FileResponse` **only if** `Path.resolve()` is inside the resolved output directory; otherwise
404. `kind` is matched against a literal whitelist, never used to build a path.

The user never supplies a path — but company and role names *do* flow into filenames through
`build_output_paths()`, so the guard is what makes that safe by construction rather than by
trusting the slug function. A unit test covers a traversal-shaped company name.

### 8. Localhost binding is the default and is tested (criterion 35)

`web/__main__.py` exposes `main()` running uvicorn with `host="127.0.0.1"` (module constant
`DEFAULT_HOST`), `port=8000`, `reload=False`. Started with `python -m cv_writer.web`. No
authentication, no session cookie, no CORS middleware — criterion 35 says single-user localhost,
and adding half an auth story would be worse than none.

A unit test asserts `DEFAULT_HOST == "127.0.0.1"` and that no CORS/auth middleware is installed
on `create_app()`. Binding to `0.0.0.0` stays possible for someone who edits the call
deliberately; it is not reachable by accident or by flag.

**Rejected: a `--host` CLI flag.** A flag is an invitation. The spec's "must not be exposed
publicly in this version" is better served by making exposure an edit than an option.

### 9. CI runs the whole suite, with Chromium installed (criterion 36)

`.github/workflows/ci.yml` gains one step between "Install dependencies" and the test step:

```yaml
- name: Install Chromium (Playwright)
  run: playwright install chromium --with-deps
```

`--with-deps` matters on `ubuntu-latest`. The test step changes from
`pytest tests/unit tests/integration -q` to `pytest tests -q`, so `tests/e2e/` actually runs —
criterion 37 asks for an e2e test, and a test CI does not execute is not evidence.

**Consequences:** CI goes green for the first time since slice 3, which *is* criterion 36's
acceptance evidence. Job time grows by the Chromium download plus real PDF renders; no caching
is added in this slice — measure first, optimise if it becomes annoying.

### 10. Criterion 26's font shortlist admits the metric-compatible libre twins

Added after decision 9 was implemented, because the newly-working CI immediately failed on it.

The first CI run with Chromium installed failed
`tests/integration/generation/test_pdf_render.py::test_pdf_font_is_on_the_documented_shortlist_and_embedded`
with `LiberationSans-Bold` not in the shortlist. The cause is not a slice 5 defect: `cv.html.jinja`
asks for `Arial, Helvetica, sans-serif`, and `ubuntu-latest` ships neither, so Chromium fell back
to Liberation Sans. On the maintainer's Windows box Arial exists and the test had always passed.
The bug was latent through slices 3 and 4 and only became visible once CI could actually run a
browser — which is the wiring in decision 9 doing its job on its first run.

**Decision:** name `"Liberation Sans"` explicitly in the template's font stack *after*
Arial/Helvetica, and widen `FONT_SHORTLIST` to include the metric-compatible libre equivalents —
Liberation Sans ≡ Arial, Liberation Serif ≡ Times New Roman, Carlito ≡ Calibri. These are
glyph-width-identical by design, so the page lays out the same regardless of which one renders,
and criterion 26's real requirements (widely available, screen-and-print legible, non-decorative,
embedded, no webfont that can fail to load) hold identically for either name. Windows and macOS
still render Arial; Linux renders its twin *by recorded choice* instead of by silent OS fallback.

**Rejected: installing `ttf-mscorefonts-installer` in CI** so the literal shortlist renders
everywhere. It needs an interactive EULA accepted through `debconf`, its apt source is a known
flake, and it drags Microsoft font licensing into CI — real cost taken on purely to avoid
amending a shortlist whose purpose is already satisfied.

**Rejected: pinning the template to Liberation Sans on every platform.** Byte-identical output
across OSes is attractive, but it changes what the maintainer's own CVs look like in order to fix
a CI problem — a product change wearing a build fix's clothes.

**Rejected: skipping the assertion when Arial is absent.** That re-hides the exact cross-platform
gap CI had just surfaced, and leaves criterion 26 unverified on the only platform CI runs.

**Consequences:** criterion 26's shortlist is now six named families plus their documented metric
twins. A CV generated on Linux and one generated on Windows are visually equivalent, not
byte-identical. Regression tests in `tests/integration/generation/test_render_html.py` pin both
halves — the stack names the twin, and the shortlist accepts it.

## New runtime dependencies

| Package | Version | Why |
|---|---|---|
| `fastapi` | `0.141.1` (constrained `>=0.115,<1`) | The server-rendered UI framework named in the spec's technical shape and deferred to this slice by ADR 0002. |
| `uvicorn[standard]` | `0.52.3` (constrained `>=0.30,<1`) | ASGI server to actually run it; `python -m cv_writer.web` is the entry point. |
| `python-multipart` | `0.0.32` (constrained `>=0.0.9,<1`) | FastAPI cannot parse HTML form POSTs without it. Every route in criterion 32's flow is a form. |

Dev extra gains `httpx` (`0.28.1` installed, constrained `>=0.27,<1`) — required by
`fastapi.testclient.TestClient`, which drives the e2e tests **without binding a socket**.

Versions above are what actually installed in this dev environment (`pip install fastapi
"uvicorn[standard]" python-multipart httpx`), verified rather than guessed — same posture ADR
0002/0004 took with their own dependency tables.

## Consequences

- `main` goes CI-green for the first time since slice 3 merged (criterion 36) — the workflow's
  own placeholder-framing comment is retired.
- The web layer adds three new runtime dependencies but touches no existing module's behavior;
  `profile`/`db`/`ingestion`/`matching`/`generation` stay importable and testable with zero web
  framework installed, mechanically enforced by decision 1's AST test.
- In-progress drafts do not survive a server restart (decision 3) — acceptable given this tool's
  localhost, single-user, single-session scope; finished applications are unaffected since they
  live in SQLite from the moment `/drafts/{id}/confirm` succeeds.
- No authentication, no CORS, no `--host` flag (decision 8) — this version is not safe to expose
  beyond localhost, by design, matching criterion 35 and the spec's own "Out of scope" section.
