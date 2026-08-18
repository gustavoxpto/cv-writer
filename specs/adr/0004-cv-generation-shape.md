# ADR 0004: CV generation, guardrails, and output shape

- **Status:** accepted
- **Date:** 2026-08-18

## Context

Slice 4 of `specs/features/001-cv-writer.md` (criteria 17-28) introduces the LLM for the first
time — behind an interface, and only behind validators that can reject its output — plus the
anti-fabrication guarantee, the PT-PT `brasileirismos` checker, and the Markdown/PDF/plain-text
output pipeline. ADR 0002 explicitly deferred two things to this slice: the `Rephraser` LLM
interface, and the PDF renderer (flagging the spec's own open question 2, a WeasyPrint spike on
Windows, as still open). Slice 2's and slice 3's pairing notes also both flagged a stable
bullet-id scheme as an open point this slice must resolve. Seven small library/design decisions
need pinning down before code, per this repo's own "ADR before code" convention.

## Decisions

### 1. Stable bullet id: `Bullet` grows a real `id` field

`Bullet` (in `profile/models.py`) gets a required `id: str` field, authored in
`data/profile.yaml` exactly like `JobHistory.id` already is. `Profile`'s cross-validator gains a
check that bullet ids are unique **across the whole profile**, not just within one job history —
criterion 18 says "the `id` of the profile bullet," a single flat id, and the anti-fabrication
validator (criterion 19) needs to resolve a bare id to a bullet without a history id alongside it.

**Rejected: `(history_id, bullet_index)` as the canonical id shape.** This is what
`matching/models.py`'s `EvidenceBullet` already uses internally, and both prior pairing notes
flagged it as the "cheap" option. It fails as a *citation* id because `bullet_index` shifts
silently if a bullet is ever reordered/added/removed in `data/profile.yaml` — an old citation
would repoint at the wrong bullet with no error raised anywhere.

**Rejected: derive the id from the database's surrogate key.** `db/migrations/0001_init.sql`
declares `bullets.id INTEGER PRIMARY KEY AUTOINCREMENT`, and `db/profile_store.py`'s
`load_profile_into_db()` does `DELETE FROM bullets` followed by a full re-`INSERT` on **every**
profile reload (its own docstring: "clears and repopulates them wholesale," which is what keeps
reloads idempotent without per-row upsert logic). That means the surrogate id is not stable
across reloads — a CV generated today could cite a bullet id a profile reload tomorrow silently
reassigns to a different bullet. Not usable as a long-lived citation.

`matching/models.py`'s `EvidenceBullet` (`history_id` + `bullet_index`) is left exactly as-is —
it identifies a *ranking candidate*, not a *citation*, and slice 3's tests already cover it.
`generation/source_ids.py` is the one new module that turns a ranking candidate into a citable
id (`bullet_source_id(profile, evidence) -> str`, looking up
`profile.job_histories[...].bullets[bullet_index].id`), keeping the churn at the boundary where
the new concept is actually needed.

Per-application extra input (criterion 17) needs the same "citable id" treatment with nothing in
the profile to derive it from: `ExtraInput.id: str`, assigned `extra-1`, `extra-2`, … in
submission order when not supplied. Profile bullet ids and extra-input ids share one string
namespace via `source_ids.resolve_source(source_id, profile, extra_inputs)`.

**Consequences:**
- `data/profile.example.yaml` and every full-profile fixture under
  `tests/unit/profile/fixtures/*.yaml` need a `id:` field added to each bullet.
- New DB migration `0002_stable_bullet_ids.sql`, **additive only** (CLAUDE.md's hard rule #1
  forbids `DROP`/`TRUNCATE` without fresh explicit permission every time, so a "recreate the
  table" migration is off the table): `ALTER TABLE bullets ADD COLUMN bullet_id TEXT;` +
  `CREATE UNIQUE INDEX idx_bullets_bullet_id ON bullets(bullet_id);`. The existing surrogate
  `id` column is left in place, just no longer used for citation.
- `application_bullet_sources.profile_bullet_id` keeps its declared `INTEGER` column
  unchanged. SQLite's type-affinity rules mean a TEXT value that isn't a well-formed integer
  literal (our ids look like `job-acme-2020-b1`) is stored as TEXT regardless of the column's
  declared affinity — no migration is needed there. This is a deliberate, documented looseness
  (the declared type no longer matches what's stored), not an oversight; a future ADR can clean
  it up with a proper recreate-migration once real data exists and that operation can be
  confirmed explicitly with a human.
- `Application.profile_bullet_ids` changes from `list[int]` to `list[str]` in
  `db/track_record.py`.

### 2. PDF renderer: headless Chromium via Playwright — no WeasyPrint spike

Chromium is already a proven, working runtime dependency on this exact Windows dev environment
(slice 3's ingestion tier-2 tests exercise it today), and the spec's own "Technical shape"
section already leans this way ("this strengthens the case against WeasyPrint noted in open
question 2" — one dependency justified twice, for both PDF render and ingestion tier 2). Spending
a session evaluating WeasyPrint as an alternative to something already installed and proven twice
over isn't worth it; this decision closes open question 2 by reasoning rather than by spiking new
code.

### 3. Markdown → HTML: the `markdown` package (Python-Markdown), core renderer only

`markdown>=3.10,<4`. Zero transitive dependencies (matches ADR 0003's minimal-footprint
posture — `pip install markdown` pulls nothing else in), long-maintained, simple
`markdown.markdown(text)` API. Its **core** renderer has no table support unless the `tables`
extension is explicitly enabled — criterion 26's "no tables" ATS-safety rule is enforced by
*never opting into that extension*, not by post-processing HTML to strip tables back out.
`mistune` was the other candidate considered (also dependency-free, faster) but Python-Markdown's
wider adoption and simpler API make it the more legible choice for a build-to-learn repo.

### 4. Fonts: no bundled font files — rely on Chromium's automatic PDF font embedding

The documented shortlist (Arial/Helvetica, Georgia, Calibri, Verdana, Times New Roman) are
Microsoft/Monotype-licensed font families, not freely redistributable as binary files in a git
repo. The print template's CSS references a shortlisted font **by name only**
(`font-family: Arial, Helvetica, sans-serif;` — no `@font-face`, no webfont). These are
standard pre-installed Windows fonts, so Chromium renders the page with the real font already on
the system. Headless Chromium's `page.pdf()` embeds (subsets) whatever font actually rendered the
page automatically — this is default PDF-export behavior in Chromium's print pipeline, not
something this codebase needs to build. Criterion 26's tests assert the *result*: the PDF's
`/BaseFont` name is on the documented shortlist, and a `/FontFile`/`/FontFile2`/`/FontFile3` key
is present on its `/FontDescriptor` (proof of embedding) — never that the repo ships a font
binary.

### 5. `pypdf` for page-count / text-extraction / font-inspection

`pypdf>=6,<7`. Pure Python (no C toolchain needed on Windows), actively maintained, covers every
PDF-reading need this slice has: `len(reader.pages)` for page count (criterion 24's page-fit
measurement), `page.extract_text()` for criterion 26's "extracted text matches the Markdown
source" test, and `page["/Resources"]["/Font"]` + `/FontDescriptor` inspection for the
font-shortlist/embedding assertions. Used identically by production code
(`generation/page_fit.py`, at generation time) and by integration tests — one library, one
behavior, no test/production drift.

### 6. PT-PT `brasileirismos` checker: versioned YAML data file

`src/cv_writer/generation/data/pt_pt_terms.yaml`: a top-level `version: <int>` plus a list of
entries (`id`, `category` — `lexis`/`progressive`/`clitic`/`orthography`, `pattern`, `is_regex`,
`replacement`, `note`). Seeded with the spec's six named lexis pairs (celular→telemóvel,
time→equipa, arquivo→ficheiro, tela→ecrã, gerenciar→gerir, planejamento→planeamento) plus one
progressive-tense regex entry (`estar + gerúndio` vs. PT-PT `estar a + infinitivo`).

Matching reuses `ingestion.requirements.word_boundary_pattern()` for literal (`is_regex: false`)
entries — one shared boundary-regex implementation across the codebase, as that helper's own
docstring already advertises — and `re.compile(pattern, re.IGNORECASE)` directly for regex
entries. The checker scans the generated Markdown **line by line**
(`text.splitlines()`), so a hit reports `line_number` + `line_text` + `replacement`, satisfying
criterion 21's exact wording ("reports the offending line and its PT-PT replacement").
"Versioned, extendable without touching code" means: adding a brasileirismo is a YAML edit plus a
`version` bump, no Python change; a unit test asserts `version` is present and is an int so a
forgotten bump fails loudly. `PyYAML` is already a dependency — no new one needed for this data
file.

### 7. Anti-fabrication numeric-claim check (criterion 19c), concretely

`extract_numeric_tokens(text)`: one regex over the *generated bullet text* matching a signed
number (optional `+`/`-`), digits with optional `.`/`,` separators, and an optional suffix (`%`,
one of `k`/`K`/`m`/`M`/`b`/`B`, or a short duration word — `min`/`hr`/`day`/`week`/`month`/
`year`). Deliberately permissive on extraction: over-flagging candidate tokens is safe (more
gets checked); under-extraction is the real danger, since it would let a fabricated number slip
past unchecked.

- If the bullet's cited source resolves to a `Bullet` with `metric is None`: **any** extracted
  numeric token is an automatic reject — there is nothing in the source to justify a number at
  all.
- If the source `Bullet` has a `Metric`: build one haystack string,
  `f"{metric.value} {metric.unit or ''} {metric.baseline or ''}"`. Every extracted token from the
  generated bullet must appear as a case-insensitive substring of that haystack — not re-parsed
  into a number, deliberately, matching the repo's existing "don't force a numeric parse and
  invent precision" posture on `Metric.value` itself (see `profile/models.py`'s own comment on
  `Metric`). A token that isn't found is a reject, naming the offending line and the specific
  token.
- A bullet whose source resolves to an `ExtraInput` (free per-application text, not a profile
  bullet) has no `Metric` to check against at all in this slice — treated the same as "no
  metric": any numeric claim from it is rejected. Criterion 19c only promises checking against
  "its source bullet's metrics"; an extra input has none, so nothing from it is trusted as a
  number.

**Worked examples**, from `Metric(value="-77%", unit="p99 latency",
baseline="from 1.4s to 320ms")`:
- Generated: *"Cut checkout p99 latency by 77%, from 1.4s to 320ms."* → tokens
  `["77%", "1.4s", "320ms"]`, haystack `"-77% p99 latency from 1.4s to 320ms"` → all three are
  substrings → **pass**.
- Generated: *"Cut checkout p99 latency by 80%, from 1.4s to 320ms."* → token `"80%"` is not a
  substring of the haystack → **reject**, naming the line and `"80%"`.

**Known trade-off, deliberately accepted:** a number present in a bullet's STAR narrative
(situation/task/action/result) but never promoted into a `Metric` field is still rejected if the
LLM repeats it — a strict reading of "not present in its source bullet's *metrics*" (19c says
metrics, not "bullet text"). This pushes "promote this number to a real `Metric`" onto the
profile author rather than loosening where the validator will accept numbers from. Flagged for
the PR's "reviewer: worth a look" section as the trade-off most likely to need revisiting against
real postings.

### 8. Language detection + PT-PT/PT-BR resolution: curated stopword frequency, no NLP/LLM

Matches ADR 0003's already-established posture ("curated dictionaries + regex phrase matching, no
NLP/LLM") and the spec's own open question 4 framing. `generation/language.py`:
`SUPPORTED_LANGUAGES` is a small, hand-picked set of high-signal function words per language
actually relevant here — English and Portuguese to start. There's no value detecting a language
outside what the tool would ever accept, since criterion 20 refuses any language not already in
`profile.languages` regardless of how confidently it was detected.

`detect_posting_language(raw_text)` tokenizes (`\w+`), lowercases, counts stopword hits per
language, and picks the highest-scoring one; a near-tie or low hit-ratio returns
`confidence="low"` rather than guessing.

PT-PT vs. PT-BR is a **sub**-decision entered only once Portuguese is detected:
1. If `Posting.country` is set (already a field on `ingestion.models.Posting`), map it through a
   small curated `country → {"pt-pt", "pt-br"}` dictionary (Portugal/Angola/Mozambique/… →
   `pt-pt`; Brazil → `pt-br`).
2. If country is absent or unmapped, scan the posting text itself against `pt_pt_terms.yaml`'s
   BR-lexis entries (reusing the same data file this checker already loads, for a second
   purpose) — a posting that itself uses "celular"/"gerenciar" is very likely Brazilian-market
   phrasing.
3. If still ambiguous, don't guess: return `variant=None, confidence="low"` and surface it as an
   explicit user choice — exactly what criterion 20's "shown to the user, and overridable before
   generation" exists for.

`resolve_output_language(posting, profile, override=None)` cross-checks the detected (or
overridden) language against `profile.languages` at a minimum "working" proficiency rank; a
language below that rank (or not in the profile at all) returns `allowed=False` with a reason
naming the language — criterion 20's refusal case.

## New runtime dependencies

| Package | Version | Why |
|---|---|---|
| `anthropic` | `>=0.122,<1` | `ClaudeRephraser`'s real implementation — structured outputs via `client.messages.parse(..., output_format=RephraseOutput)`, `claude-opus-5` per project default. |
| `markdown` | `>=3.10,<4` | Markdown → HTML for the print template (decision 3). |
| `pypdf` | `>=6,<7` | Page count / text extraction / font inspection, shared by production and tests (decision 5). |
| `Jinja2` | `>=3.1,<4` | The print template engine (spec's stated technical shape). Has no framework dependency, so it's safe to bring in now, ahead of slice 5's FastAPI. |

Versions above are what actually installed in this dev environment (`pip install anthropic
markdown pypdf Jinja2`), verified rather than guessed — same posture ADR 0002 took with the
Python version itself.

## Consequences

- `0002_stable_bullet_ids.sql` is additive-only; no destructive schema change happened, and none
  is planned until real track-record data exists and a recreate-migration can be explicitly
  confirmed with a human, per CLAUDE.md's hard rule #1.
- `Application.profile_bullet_ids`'s type change (`int` → `str`) is a small breaking change to
  that model's shape, but nothing outside this repo depends on it yet (`db/track_record.py`'s own
  docstring: "No generation pipeline calls this yet").
- The strict "metrics only, not full STAR text" fabrication-check trade-off (decision 7) is a
  deliberate false-rejection risk to watch against real postings — same "watch this" posture ADR
  0003 already established for its own heuristics.
- `data/profile.example.yaml` and every profile fixture with bullets need a one-time `id:` field
  addition; done once, in this slice, alongside the schema change.
