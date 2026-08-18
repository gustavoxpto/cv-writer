# PR body — CV Writer slice 4: generation + guardrails + output (001, criteria 17-28)

Branch: `feat/001-slice4-generation-guardrails-output` → `main`.
Title: `feat(001): slice 4 — generation + guardrails + output (criteria 17-28)`.

---

## What & why

Implements slice 4 of [`specs/features/001-cv-writer.md`](../../specs/features/001-cv-writer.md):
the LLM enters the pipeline for the first time, and only behind the validators that can
reject its output. Per-application extra input (17), a bounded `Rephraser` interface tested
entirely offline (18, 22, 23), the anti-fabrication validator (19), language detection and
PT-PT/PT-BR handling (20-21), and Markdown/PDF/plain-text output with a real, PDF-measured
page-fit algorithm (24-28). Resolves two open points carried over from slices 2-3 (the stable
bullet-id question) and the spec's own open question 2 (PDF renderer). Still headless — the
UI is slice 5.

## What's in it

- **`src/cv_writer/generation/`** (new package, 16 modules + a versioned data file + a Jinja2
  print template):
  - `models.py` — `ExtraInput`, `GeneratedBulletDraft`/`RephraseOutput` (the Rephraser's
    structured-output shape), `GeneratedCv`/`GenerationFailure` (mirrors `ingestion/models.py`'s
    result/failure pattern), `ValidationFailure`.
  - `pt_pt_checker.py` + `data/pt_pt_terms.yaml` — versioned, data-driven `brasileirismos`
    checker (criterion 21), written and tested before any LLM code exists.
  - `source_ids.py` — resolves a citable id to a profile bullet or extra input; turns a
    matching-layer `EvidenceBullet` (ranking candidate) into a citation.
  - `validator.py` — the anti-fabrication guarantee (criterion 19): no-source-id, unknown-
    entity, numeric-claim, and claimed-direction checks, every one re-deriving truth from the
    profile rather than trusting the LLM's own citation.
  - `language.py` — curated stopword-frequency detection, PT-PT/PT-BR resolution, working-
    proficiency refusal (criterion 20), sharing `profile/proficiency.py`'s vocabulary with
    `matching/matcher.py`.
  - `rephraser.py` — `Rephraser` Protocol, `FakeRephraser` (used by every test), `ClaudeRephraser`
    (real: Claude API structured outputs, env-only key read, never exercised by this test suite).
  - `pipeline.py` — `generate_cv()`: rephrase → validate → PT-PT check → accept/reject.
  - `render_text.py` / `render_html.py` / `render_pdf.py` / `pdf_inspect.py` — Markdown →
    HTML (core `markdown` renderer only, no tables — the ATS-safety mechanism) → PDF via
    headless Chromium; `pdf_inspect.py` reads page count/text/embedded fonts back, used by
    both production (`page_fit.py`) and tests.
  - `page_fit.py` — the real, PDF-measured page-fit algorithm (criterion 24), replacing
    `matching/ranking.py`'s char-budget heuristic as the authoritative mechanism.
  - `output_paths.py` — deterministic, versioned, collision-free (criterion 28).
  - `build_application.py` — pure mapper into the existing `db.track_record.Application`; no
    DB I/O in `generation/` at all.
- **`profile/models.py`** — `Bullet` gains a real, stable, globally-unique `id` field
  (replacing the composite `(history_id, bullet_index)` open point flagged by slices 2 and 3),
  rejecting a purely-numeric value (see review notes). `data/profile.example.yaml` and every
  profile test fixture updated.
- **`profile/proficiency.py`** (new) — `WORKING_PROFICIENCY_LEVELS`, shared by `matching/
  matcher.py` and `generation/language.py` (they'd quietly drifted apart — see review notes).
- **`db/migrations/0002_stable_bullet_ids.sql`** — additive only (`ALTER TABLE ... ADD COLUMN`
  + unique index), no destructive schema change. `Application.profile_bullet_ids` type fixed
  `list[int]` → `list[str]`.
- **ADR 0004** records all eight technical decisions (bullet id, PDF renderer — no WeasyPrint
  spike, Markdown library, fonts, `pypdf`, PT-PT data format, numeric-claim algorithm,
  language detection) before any generation code was written.
- **New runtime dependencies**: `anthropic`, `markdown`, `pypdf`, `Jinja2`.
- **~90 new tests** (full suite: 105 → 189), `ruff check` clean.

## Acceptance criteria covered

Criteria 17-23 (spec section D): per-application extra input recorded and promotion-suggested;
LLM bounded to rephrasing/ordering behind one interface, tested entirely offline; anti-
fabrication validator naming the offending line; language detected/shown/overridable/refused
below working proficiency; PT-PT `brasileirismos` checker; `ANTHROPIC_API_KEY` read from
environment only, never persisted. Criteria 24-28 (spec section E): real PDF-measured page-fit
with an honest drop list; Markdown source rendered through one consistent, ATS-safe, B&W,
documented-font-shortlist PDF template with selectable/extractable text matching the source;
plain-text variant; deterministic, versioned, never-overwriting output paths.

## Review pass (before this PR)

Two completed `/code-review` passes (a third started but hit a session usage limit before
finishing — the first two already surfaced and fixed everything load-bearing) found ~13 real,
directly-reproduced issues and fixed every one, one regression test each — full detail and
rationale in the pairing note's "Review pass" section. Headlines: numeric-claim substring
matching let near-miss fabrications through ("7%" inside a true "-77%") and separately pulled
spurious digits out of ordinary tech jargon ("p99" → "99"), both fixed with digit-adjacency/
word-boundary guards; a direction-reversed claim ("increased" against a true decrease) passed
digit-only matching, so a curated increase/decrease word check was added; the entity-
fabrication cue-phrase heuristic false-positived constantly on ordinary prose and was narrowed
from five cue words to one; a hyphenated English tech compound ("real-time") false-positived
the PT-PT checker's `time` entry; `matching/matcher.py` and `generation/language.py` had
silently drifted onto two different working-proficiency vocabularies for the same field; an
override language in its natural capitalized form broke the profile-support lookup on case
alone; a stale evidence reference raised an uncaught exception instead of a clean
`GenerationFailure` (and writing that regression test surfaced a second related gap: zero
surviving evidence crashed on `GeneratedCv`'s own `min_length` constraint); a purely-numeric
bullet/extra-input id silently coerced to SQLite's INTEGER storage class; `resolve_source()`
had no collision guard between the two id namespaces it resolves; PT-PT regex entries weren't
cached like the literal-entry path; and `embedded_fonts()` reported a real, embedded Arial
font as not embedded — traced to Chromium's Type0/CIDFontType2 composite-font structure, whose
descriptor lives on the descendant font, not the top-level font dict.

One finding was deliberately **not** code-fixed: `build_output_paths()` checks existence only,
not a reservation, so two concurrent runs could compute the same path — documented in the
module itself as a deliberate limitation given the spec's own "localhost, single-user" scope.

## Learning notes

- **Every "CONFIRMED" finding in both completed passes came from a direct repro script run
  against this repo's own `.venv`**, not static reading alone — `extract_numeric_tokens(...)`,
  `resolve_output_language(..., override="English")`, a small debug script against a real
  rendered PDF for the font-embedding bug. Worth carrying forward as a review habit for this
  repo generally, not just something the review skill happened to do this time.
- **The heuristics that shipped with a worked example (ADR 0004's numeric-claim examples) were
  trivial to regression-test the moment a review pass found a gap; the ones that didn't (the
  entity check, the PT-PT `time` entry) needed a second pass to even notice.** Writing the
  worked example down is cheap insurance.
- **A destructive-looking migration usually isn't the only option** — CLAUDE.md's hard rule
  against unapproved deletion forced an additive-column answer for the stable-bullet-id
  schema change instead of a table recreate, and that answer turned out simpler too, not just
  safer.

## Checklist

- [x] Spec in `specs/features/` signed off before implementation — `001-cv-writer.md`,
      criteria 17-28 targeted
- [x] ADR written before code — `specs/adr/0004-cv-generation-shape.md`
- [x] Tests written before/alongside implementation, every test citing its criterion
- [x] Local checks passing — `ruff check` clean, `pytest` green (189 passed)
- [x] No secrets committed — `ANTHROPIC_API_KEY` never written to disk/DB/artifact, read from
      environment only at call time inside `ClaudeRephraser`; `.env.example` documents the
      variable name only, no real value; no network calls in tests (criterion 22 — verified by
      grep, `ClaudeRephraser`/`anthropic.Anthropic(` appear only in `rephraser.py` itself)
- [x] Pairing notes added — `pairing/sessions/2026-08-18-slice4-generation-guardrails-output.md`,
      including the pre-commit review passes

### Reviewer: worth a look

1. **The entity-fabrication check (criterion 19b) is English-only and still a cue-word
   heuristic ("at <Capitalized phrase>"), not real NER.** Narrowed hard during review to cut
   false positives; the trade-off is it will miss fabricated employers that don't follow that
   exact idiom, and won't catch anything in Portuguese-language bullets at all yet.
2. **The PT-PT `brasileirismos` list only has one entry per category beyond the spec's six
   named lexis examples** (one progressive-tense regex, no clitic-placement or orthography
   entries yet) — same "ceiling" the spec's own open question 5 already flags; needs real
   PT-PT postings thrown at it.
3. **The anti-fabrication numeric check only verifies against a bullet's `Metric` fields, not
   its full STAR text** — a number present in `situation`/`task`/`action`/`result` but never
   promoted into `Metric` is still rejected if the LLM repeats it. Deliberate (ADR 0004
   decision 7): pushes "promote this number" onto the profile author rather than loosening
   where the validator trusts numbers from. Worth confirming that's the right call in practice.
4. **`build_output_paths()`'s existence-check-only versioning isn't safe under concurrent
   runs** (see "Review pass" above) — a deliberate non-fix given this tool's single-user scope,
   flagged in case that scope assumption ever changes.
5. **The third `/code-review` pass didn't finish** (session usage limit). The first two passes
   were thorough and found real, high-value issues independently corroborating each other's
   top findings from prior slices' review habit — but a maintainer who wants extra assurance
   before merging may want to run one more pass fresh.
