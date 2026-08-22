# Design: 003-full-document-language-localization

- **Spec:** `.specs/features/003-full-document-language-localization/spec.md`
- **Date:** 2026-08-21
- **ADR:** `specs/adr/0006-output-language-localization-shape.md`

## Shape

Two defects, two places. One is a *decision* defect (`language.py` allows a language the tool has
no business writing in); the other is a *rendering* defect (`render_text.py` writes three English
words regardless of that decision). The shape below keeps those concerns apart on purpose: exactly
one module decides what language the document is in, and every other module treats that answer as
already-settled data.

```
                POST /drafts/{id}/generate
                          |
        src/cv_writer/web/routes.py::generate_draft_cv()
                          |  language_override (free-form form field)
                          v
        src/cv_writer/generation/pipeline.py::generate_cv()
                          |
                          +--(1)--> generation/language.py::resolve_output_language()
                          |           SUPPORTED_LANGUAGES gate  <- AC-001, AC-002
                          |           profile-proficiency gate  <- AC-003
                          |           returns LanguageResolution(allowed, reason, reason_code)
                          |
                          |    if not allowed --> GenerationFailure --> 422 re-render  <- AC-006
                          |                       (existing early return; nothing new)
                          |
                    ======+====== THE LLM BOUNDARY ==============================
                          |        nothing above this line may call a model;
                          |        nothing below it may re-decide the language
                          v
                    rephraser.rephrase(request)   <- first Anthropic call
                          v
                    GeneratedCv(language=<resolved>, ...)
                          |
                          v
        generation/render_text.py::render_markdown(cv, profile)
                          |  reads cv.language, looks up:
                          v
        generation/headings.py::section_headings(language)   <- AC-004  (new module)
                          |
                          v
        render_plain_text()  /  render_html()  /  render_pdf()
```

### Components

| Component | New/changed | Owns | Criteria |
|---|---|---|---|
| `src/cv_writer/generation/headings.py` | **new** | The localized structural strings, as an in-code mapping `language -> SectionHeadings(experience, education, skills)`, plus `section_headings(language)` which raises on an unknown language rather than falling back to English. Imports nothing from `cv_writer`. | AC-004 |
| `src/cv_writer/generation/render_text.py` | changed | Document layout. After this slice it holds **no user-visible words of its own** — every heading comes from `headings.py`, keyed by `cv.language`. `render_plain_text()` needs no edit; it inherits by construction. | AC-004 |
| `src/cv_writer/generation/language.py` | changed | The only module that decides an output language. Gains a `spanish` stopword set, the `SUPPORTED_LANGUAGES` gate ahead of the profile check, and a `LanguageRefusal` reason code on `LanguageResolution`. | AC-001, AC-002, AC-003 |
| `src/cv_writer/generation/pipeline.py` | **unchanged** | Already returns `GenerationFailure` on `not allowed` before it constructs a `RephraseRequest`. AC-006 needs no new control flow — it needs a sensor that pins the existing ordering. | AC-006 |
| `src/cv_writer/web/routes.py`, `web/templates/draft.html.jinja` | **unchanged** | `generate_draft_cv()` already re-renders with `generation_failure` at 422, and the template already prints `generation_failure.reason`. AC-006's "reaches the user" half is existing behaviour this slice puts under test on this path for the first time. | AC-006 |
| `specs/features/001-cv-writer.md` | amended | Criterion 26's ATS bullet, plus a new dated Revision-log entry. Amendment only — nothing is removed from the file. | AC-005 |
| `tests/unit/generation/test_language.py` (extended), `tests/unit/generation/test_render_text.py` (**new file** — `render_markdown()` has no unit test today), `tests/unit/generation/test_render_text_has_no_hardcoded_headings.py` (**new**), `tests/integration/generation/test_generation_pipeline.py` (extended), `tests/unit/web/` (extended), `tests/unit/scripts/test_spec_001_criterion_26_amendment.py` (**new**) | tests | The sensors. | all |

### Where the resolved language actually comes from (question (b), answered against the code)

`render_markdown()` takes `(cv, profile)` and needs a language it does not currently look at. It
does **not** need a new parameter: `GeneratedCv.language` is already populated, already correct,
and already the resolved value at both real call sites. Verified, not assumed:

- `pipeline.py::generate_cv()` constructs the only `GeneratedCv` this application ever produces and
  sets `language=language_resolution.detected` — the same value it fed to
  `RephraseRequest.target_language`, so headings and bullets cannot disagree by construction.
- Call site 1, `generation/write_output.py:59` — `render_markdown(cv, profile)` on that object.
- Call site 2, `web/routes.py:110`, inside `_measure_page_count()` —
  `render_markdown(narrowed, profile)` where `narrowed = _narrow_cv(cv, source_ids)`, and
  `_narrow_cv` copies `language=cv.language` through verbatim (`routes.py:98`). The same `_narrow_cv`
  result reaches `write_artifacts()` from `confirm_application()`.

There is no third call site in `src/`. So `render_markdown()` reads `cv.language`, and its signature
does not change. ADR 0006 decision 2 records why an explicit `language=` parameter was rejected: in
short, `render_html(markdown_text, language=cv.language, ...)` already demonstrates the failure mode
of passing a value the object is carrying anyway — two places that can drift.

One honest wart, pre-existing and out of scope: that same `render_html` call puts
`"english"`/`"portuguese"` into the HTML `lang` attribute, which is not a valid BCP-47 tag, and
after this slice it will also put `"spanish"` there. That is OQ-3 — still open, still non-blocking.

### The AC-001 control flow (question (c))

Today `resolve_output_language()` resolves a language and then asks one question: does the profile
support it? AC-001 inserts a prior question with a different subject — not "can *this person* write
in it" but "can *this tool* write in it". The ordering matters because both answers can be "no" for
different reasons and the user needs the actionable one. Telling someone *"'french' is not listed in
the profile's languages"* invites them to add French to `profile.yaml`, after which the tool would
still produce an English-headed document.

```python
def resolve_output_language(posting, profile, override=None, *, pt_terms=None) -> LanguageResolution:
    if override is not None:
        language = override.strip().lower()
    else:
        language = detect_posting_language(posting.raw_text).language

    # AC-001: the tool's own capability, checked BEFORE the profile's.
    if language not in SUPPORTED_LANGUAGES:
        return LanguageResolution(
            detected=language,
            variant=None,
            allowed=False,
            reason_code=LanguageRefusal.UNSUPPORTED_LANGUAGE,
            reason=(f"'{language}' is not a language this tool can write a CV in "
                    f"(supported: {', '.join(sorted(SUPPORTED_LANGUAGES))})"),
        )

    variant = _resolve_pt_variant(posting, pt_terms) if language == "portuguese" else None
    allowed, reason, reason_code = _check_profile_supports(language, profile)
    return LanguageResolution(detected=language, variant=variant, allowed=allowed,
                              reason=reason, reason_code=reason_code)
```

Return shape: `LanguageResolution` keeps `detected`, `variant`, `allowed`, `reason`, and gains
`reason_code: LanguageRefusal | None = None` — a three-member `str`-valued `Enum`
(`UNSUPPORTED_LANGUAGE`, `NOT_IN_PROFILE`, `BELOW_WORKING_PROFICIENCY`), same
`class X(str, Enum)` idiom as `generation/models.py::ExtraInputKind`. AC-001's word is
"**distinct**", and distinctness between three prose sentences is only checkable by freezing the
prose; distinctness between three enum members is checkable by `!=`. `reason` stays the human-facing
string that reaches the UI unchanged. See ADR 0006 decision 3, and concern 4 below — this is the one
addition here that no criterion names.

Two consequences of the ordering worth stating out loud:

1. The gate sits on the **resolved** language, after the override/detect fork, so it also catches
   `detect_posting_language()`'s `"unknown"` sentinel (zero stopword hits). That case currently
   refuses with "not listed in the profile's languages", which is simply the wrong explanation.
   AC-001's text names only the override case; applying it uniformly is a superset — flagged as
   concern 3 rather than smuggled in. No existing test asserts the old text on that path
   (`test_detected_language_absent_from_profile_is_refused` asserts only `reason is not None`).
2. The early return skips `_resolve_pt_variant()`, so an unsupported language no longer reads
   `pt_pt_terms.yaml` off disk on its way to being refused. A small win, not a reason.

### Where the localized strings live (question (a))

`src/cv_writer/generation/headings.py`, as a module-level mapping in Python — **not** a versioned
YAML file with a loader, a `version` field and a validator, despite spec 002 having just established
exactly that pattern next door in `ingestion/term_list.py`. Full argument and rejected options in
ADR 0006 decision 1. The short version: the YAML pattern exists so vocabulary can be extended by
someone editing *data* without touching *code*, and that is not the situation here. Adding a
language to this tool is irreducibly a code change (`SUPPORTED_LANGUAGES` is a Python dict of
stopword sets), so putting the headings in YAML would split one atomic "support Spanish" change
across two files in two formats and create a way for the halves to drift.

### AC-006's "before any LLM call" (question (d))

Traced end to end, the path from the user's click to the first byte on the wire:

`routes.py::generate_draft_cv()` (line 304) -> `pipeline.py::generate_cv()` (line 314) ->
`resolve_output_language()` (pipeline line 48) -> **`if not language_resolution.allowed: return
GenerationFailure(...)`** (pipeline lines 51-52) -> `select_bullets_within_budget()` ->
`_resolve_evidence_bullets()` -> `RephraseRequest(...)` -> **`rephraser.rephrase(request)`**
(pipeline line 64) -> `ClaudeRephraser.rephrase()` -> `import anthropic` ->
`client.messages.parse(...)` (`rephraser.py` line 91).

The exact point the refusal must happen is therefore **`generate_cv()`'s existing early return on
`not language_resolution.allowed`** — already the last decision before anything reaches the
`Rephraser` protocol, with only pure functions between. AC-006 requires **no new production code**;
it becomes true the moment AC-001 makes `allowed` False for an unsupported language. What AC-006
does require is a sensor, because "no new code" and "no protection" look identical in a diff.

The boundary being asserted is named in the diagram: **the `Rephraser` call inside `generate_cv()`
is the LLM boundary; every language decision happens above it, and no language decision happens
below it.** Its sensor is behavioural, not structural — see B2.

## Boundaries

Three. Two get tests and are therefore boundaries. The third is labelled a preference, honestly,
because it does not.

### B1 — `render_text.py` owns no user-visible words (tested)

`src/cv_writer/generation/render_text.py` must contain no string literal of its own that a reader of
the CV would see. Every such string comes from `headings.py`, keyed by the resolved language. This
is not a style rule; it is the exact defect class that produced this spec, and OQ-5's promise ("if a
later slice adds a fourth section, it adds a criterion with it") is only a promise until something
enforces it.

**Sensor:** `tests/unit/generation/test_render_text_has_no_hardcoded_headings.py`. An AST scan
(`ast.parse`, walk `ast.Constant` and the literal parts of `ast.JoinedStr`, skipping the module and
function docstrings) asserting that no string constant in the module contains two or more
consecutive ASCII letters. Modelled on `tests/unit/web/test_core_has_no_web_imports.py`, including
that file's two habits worth copying: a test that plants a synthetic violation to prove the scan
catches what it claims to, and a guard asserting the scan actually looked at something (an empty
parametrize passes trivially).

Why that rule rather than a blacklist of `"## Experience"` / `"## Education"` / `"## Skills"`: a
blacklist only catches the three words we already found. The letters rule catches the *next* one.
It is checkable against the module's real contents — after the change every literal `render_text.py`
needs is punctuation or whitespace (`"# "`, `"## "`, `" | "`, `": "`, `", "`, `"- "`, `"#"`, `""`,
`"\n"`), and every word lives in `headings.py`. If a future slice genuinely needs a literal word
here, the failing test is the conversation. That is the point.

### B2 — no language decision below the LLM boundary (tested)

`generate_cv()` must reach `Rephraser.rephrase()` only after `resolve_output_language()` returned
`allowed=True`, and nothing downstream may re-derive or override the language.

**Sensor:** behavioural, not AST — an import scan cannot express "before". A `Rephraser` double
whose `rephrase()` raises `AssertionError("the LLM was called for a refused language")`, injected
into `generate_cv()` with an unsupported `language_override`. The test asserts a `GenerationFailure`
came back carrying the refusal reason; the double not firing is what proves the ordering. Same
dependency-injection posture the repo already uses everywhere (ADR 0005 decision 4 — there is no
`unittest.mock` in this codebase, and `FakeRephraser` is already the seam).

Explicitly **not** proposed: an AST "no model client import" scan over `generation/`, the analogue
of `tests/unit/ingestion/test_no_model_calls.py`. That test exists because ingestion and matching
must *never* call a model; generation legitimately does, which is why spec 002's scan deliberately
excludes it (`DETERMINISTIC_PACKAGES = ("ingestion", "matching")`). Copying it here would be either
vacuous or a prohibition on the thing generation is for. The invariant here is about *order*, and
order is behaviour.

### B3 — `headings.py` is pure data (a preference, not a boundary)

`headings.py` imports nothing from `cv_writer` and touches no disk, so the render path does not drag
`ingestion` or the `pt_pt_terms.yaml` load in behind it, and the dependency direction
`render_text -> headings` stays trivially acyclic. Worth stating in the module docstring. It gets no
test, so by this repo's own standard it is a preference — recorded as one rather than dressed up as
a boundary.

## Decisions

| # | Decision | Alternatives rejected | Why | ADR |
|---|---|---|---|---|
| 1 | Localized headings live in a new `generation/headings.py` as an in-code mapping `language -> SectionHeadings` | (a) versioned YAML + pydantic loader, mirroring `ingestion/term_list.py` and `pt_pt_terms.yaml`; (b) a bare dict inside `render_text.py`; (c) a `gettext`/`.po` catalogue | The YAML pattern buys "extend the data without touching code", which cannot happen here: adding a language means editing `SUPPORTED_LANGUAGES`, which is Python. YAML would split one change across two formats and let them drift. A dict inside `render_text.py` violates B1 and hides the completeness pairing. `gettext` is a whole toolchain for twelve strings. | `specs/adr/0006-output-language-localization-shape.md` §1 |
| 2 | `render_markdown()` reads `cv.language`; the `(cv, profile)` signature does not change | (a) a new `language: str` parameter; (b) a new `headings: SectionHeadings` parameter (inject the strings); (c) pass the whole `LanguageResolution` through | `GeneratedCv.language` is already populated and correct at both real call sites. A parameter creates a second source of truth for a value the object already carries — exactly how `render_html(..., language=cv.language)` can drift today. Injection (b) is testable but pushes a policy decision onto every caller. | §2 |
| 3 | `LanguageResolution` gains `reason_code: LanguageRefusal \| None`, a three-member `str` Enum | (a) three distinct prose strings only, with tests asserting substrings; (b) three exception types; (c) a separate boolean `supported` flag | AC-001 asks for a reason "distinct from" two others. Distinctness of prose is only assertable by freezing prose, which then breaks on any rewording. An enum makes distinctness a property of the type. Exceptions would break `generate_cv()`'s documented "never raises on a normal rejection" contract. | §3 |
| 4 | `section_headings(unknown_language)` raises `ValueError`; it never falls back to English | (a) silent English fallback; (b) return the language name itself; (c) `dict.get` returning `None` and letting the caller decide | A silent English fallback *is* the bug this spec exists to fix — it would render the exact broken 2026-08-19 artifact with every test green. L-004 applies: prefer a loud failure to a quiet wrong result. After AC-001 the raise is unreachable through `generate_cv()`, which is the point — it is the assertion that AC-001 holds. | §4 |
| 5 | The Spanish stopword set must be disjoint from the English, Portuguese and German sets, asserted by a test | (a) add Spanish words freely and accept overlaps; (b) rework `detect_posting_language()` to weight or normalise scores | `detect_posting_language()` scores by raw set intersection and breaks ties by dict insertion order, so a word in two sets inflates both equally and the winner is decided by which key was written first. Spanish/Portuguese is the closest pair this tool has held. Reworking the scorer is in no criterion. The pre-existing `"team"` overlap between English and German is documented and left untouched — not deleted, not "fixed". | §5 |
| 6 | AC-005's sensor lives at `tests/unit/scripts/test_spec_001_criterion_26_amendment.py` and splits the file at `### Revision log` before asserting | (a) one substring check over the whole file; (b) a checksum of criterion 26; (c) matching the new wording verbatim | Detail below. A whole-file check collides with quoting the old wording in the log entry; a checksum breaks on every unrelated edit; verbatim matching makes the sensor a transcription test, which OQ-4 already concedes it cannot be. | not ADR-worthy (a test's shape, cheaply reversible) |

### AC-005's documentation sensor, concretely (question (f))

Target file: `specs/features/001-cv-writer.md` — the pre-harness layout. Spec 001 was never migrated
into `.specs/`, and `gate.py`'s artifact validators only glob `.specs/features/*/`, so amending it
trips no other sensor. The test reads the file as text and splits it once, at the `### Revision log`
heading, into `criteria_part` and `log_part`. Four assertions:

1. **The mandate is gone.** The exact string `standard section headings (Experience, Education,
   Skills)` — what the file contains today, line 152 — does not appear in `criteria_part`. Precise
   enough to be genuinely red today (L-007), and no rewording elsewhere can resurrect it.
   Restricting it to `criteria_part` is what lets the revision-log entry quote the old wording
   verbatim, which is the never-delete-shaped way to record an amendment.

   > **Correction (2026-08-21, Tasks phase) — assertion 1 as written above is wrong, and as
   > specified would have shipped a sensor that is already green before the amendment exists.**
   > The phrase is *line-wrapped* in `specs/features/001-cv-writer.md`: line 152 ends with
   > `standard section headings (Experience, Education,` and line 153 resumes with `Skills),`
   > after six spaces of indent. The contiguous string quoted above therefore does not appear in
   > the file's raw text at all — `"standard section headings (Experience, Education, Skills)" in
   > criteria_part` is `False` today — so assertion 1 would have passed against the *unamended*
   > file. That is precisely the L-007 failure the phrase "genuinely red today" claims to avoid,
   > and "line 152" above is at best half the location. The fix: normalise whitespace (collapse
   > runs to single spaces) before the phrase check, while keeping the raw text for the
   > line-anchored assertions 2 and 3. `tasks.md` T-009 carries the corrected wording and
   > additionally requires the implementer to *observe* the assertion fail against the unamended
   > file before writing the amendment. The original sentence is left standing rather than
   > rewritten, per hard rule #1 — the record of what the design got wrong is worth more than a
   > clean paragraph.

2. **Criterion 26 still exists.** `criteria_part` still has a line matching `^26\. ` and still
   contains `ATS-safe structure`. Without this, assertion 1 is dischargeable by deleting the
   criterion — the sensor would reward exactly the move hard rule #1 forbids.
3. **A dated entry records it.** In `log_part`, at least one entry matching
   `^- \*\*(\d{4}-\d{2}-\d{2})` — the form the 2026-08-17 entry already uses — whose date is later
   than `2026-08-17` and whose body mentions both `criterion 26` (case-insensitive) and `003`.
   Anchoring on the feature id rather than a phrase ties the entry to this work without dictating
   its prose, so ordinary rewording survives.
4. **The sensor is looking at a real file.** The path exists, and the split produced two non-empty
   halves — the same "assert something was actually scanned" guard both existing AST tests carry,
   because a path typo otherwise turns every assertion above into decoration.

What it deliberately does not assert: that the new wording is *good*. OQ-4 already conceded that
limit ("the test proves the amendment is present, not that it is well worded"), and a sensor that
tried would be a transcription test failing on every improvement to the sentence.

## Traceability

Every component above traces to a criterion; nothing is proposed without one.

| Criterion | Discharged by |
|---|---|
| AC-001 | The `SUPPORTED_LANGUAGES` gate ahead of `_check_profile_supports`, `LanguageRefusal.UNSUPPORTED_LANGUAGE`, tests in `tests/unit/generation/test_language.py` |
| AC-002 | `SUPPORTED_LANGUAGES["spanish"]`, the disjointness test, a Spanish detection test, a `variant is None` test |
| AC-003 | A parametrized proficiency test over all four languages (one body, four ids — the cleanest available expression of "no special-casing") |
| AC-004 | `headings.py` + `render_text.py`, a parametrized render test over four languages, a plain-text inheritance test, B1's AST sensor |
| AC-005 | The amendment to `specs/features/001-cv-writer.md` + `tests/unit/scripts/test_spec_001_criterion_26_amendment.py` |
| AC-006 | No production change; B2's exploding-`Rephraser` integration test, plus a web test POSTing an unsupported override and asserting 422 with the reason in the body |

**Reused rather than added:** `pipeline.py`'s early return, `GenerationFailure`, the 422 re-render in
`generate_draft_cv()`, `draft.html.jinja`'s `generation_failure.reason` block, the injected
`Rephraser` seam, `_narrow_cv`'s language passthrough, and the AST-scan idiom from
`tests/unit/web/test_core_has_no_web_imports.py`. The only genuinely new production module is
`headings.py`.

**Not touched, deliberately:** `data/profile.example.yaml` (no criterion asks for Spanish in the
example profile), `render_html.py`, `pt_pt_checker.py`, `validator.py`, `web/templates/`.

## Resolution of the flagged concerns (2026-08-21, after Gustavo's review)

Two of the concerns raised below were decided before Tasks. Both went back into `spec.md` rather
than being accepted as design-only, which is the C-007 discipline from spec 002: work a criterion
does not name does not ride along under an existing AC number.

- **AC-001 as a superset → the criterion was widened, not the design narrowed.** `spec.md` R-1.
  AC-001 now gates the resolved language from either door — `override` or
  `detect_posting_language()`, including its `"unknown"` sentinel — and names the ordering against
  `_resolve_pt_variant()`. The design's reasoning was accepted as correct; the criterion was what
  was too narrow.
- **`reason_code` → promoted to its own criterion, AC-007.** `spec.md` R-2. It changes a public
  model shape, so a contract item should be able to discharge it by name rather than inherit it as
  an unnamed detail of AC-001.

The spec was re-signed on both. The remaining concerns below stand as written: the French-fixture
test re-arrangement, `detect_posting_language()`'s ignored `confidence`, the post-AC-002
reachability point about fixture profiles, and OQ-2/OQ-3.

## Concerns for the human, before tasks are broken out

Flagged, not decided. None of these invents a criterion.

1. **One existing test will go red, and it must be re-arranged, not removed.**
   `tests/unit/generation/test_language.py::test_a_proficiency_level_recognized_by_matching_is_also_recognized_by_generation`
   builds a profile whose only language is **French** at `"advanced"` and asserts
   `resolve_output_language(..., override="french").allowed is True`. Under AC-001 that becomes
   False — French is not in `SUPPORTED_LANGUAGES`. The invariant that test protects is real and
   still wanted (matching and generation share one working-proficiency vocabulary; they had
   silently drifted apart once already). The fix is to re-arrange the *fixture* — German at
   `"advanced"`, override `"german"` — so the assertion is still about proficiency vocabulary and
   nothing is weakened. This will look like "the implementer edited a test to make a gate pass", so
   it wants its own task, its own commit, and this reasoning in the message.
2. **`detect_posting_language()` computes `confidence` and `resolve_output_language()` ignores it.**
   A `confidence="low"` detection silently drives generation today. Adding Spanish — the closest
   lexical neighbour Portuguese has ever had here — raises the odds of a near-tie resolved by dict
   insertion order. Decision 5's disjointness rule reduces the exposure but does not remove it. No
   criterion in spec 003 covers it. Recommend a follow-up spec rather than widening this one.
3. **Spec-precision note on AC-001.** Its text names only the `override` path. This design applies
   the gate to the resolved language, so it also covers detection's `"unknown"` sentinel and
   replaces a misleading refusal message. That is a superset of what AC-001 asks. If you would
   rather it be strictly the override case, say so now — it is one `if` either way, but the wider
   version is what makes AC-006's phrasing ("*a* language absent from `SUPPORTED_LANGUAGES`") true
   as written.
4. **Decision 3 (`reason_code`) is the one addition no criterion names.** It exists to make AC-001's
   "distinct" mechanically checkable. If you would rather keep the codebase's existing
   reason-is-a-human-string convention unbroken (`GenerationFailure.reason`,
   `IngestionFailure.reason`), the fallback is three prose strings and tests asserting a stable
   keyword in each — simpler, and brittle to rewording. Your call; this is the cheapest moment to
   make it.
5. **After AC-002 lands, AC-001's refusal is unreachable from the shipped UI with the shipped
   profile.** `data/profile.yaml` lists English, Portuguese, Spanish and German, and all four become
   supported; the override dropdown in `draft.html.jinja` is populated from `profile_languages`, so
   it can only offer those. That does not make the guard decorative: `language_override` is a
   free-form `Form("")` field that accepts any string a hand-crafted POST sends, and `profile.yaml`
   is user-editable data that gains a fifth language the day someone adds one. The AC-001 and AC-006
   tests must therefore use a profile fixture carrying an unsupported language (French at
   professional) — worth saying in the task list so nobody concludes the criterion is vacuous.
6. **OQ-2 is still open; the headings land as a draft.** "Experiência Profissional / Formação /
   Competências", "Berufserfahrung / Ausbildung / Kenntnisse", "Experiencia / Educación /
   Habilidades" are AI-proposed, not native-speaker-reviewed. Worth naming in the PR's "reviewer:
   worth a look" section. Changing one later is a one-line edit in `headings.py` plus the test's
   expected value — cheap by design, which is part of why the strings live in code.
7. **OQ-3 gets marginally worse and stays out of scope.** `render_html(..., language=cv.language)`
   will now emit `lang="spanish"` alongside the existing `lang="english"`/`lang="portuguese"` — all
   invalid BCP-47. No criterion here covers it, and the spec's "Out of scope" explicitly forbids
   changing `render_html`'s language semantics beyond staying consistent.

## Build-to-learn notes

**The thing to understand before the code lands: this feature is mostly about *who is allowed to
know* the output language, not about translating three words.**

The obvious fix is four lines — a dict of headings and a lookup in `render_text.py`. That fix works
and leaves the actual hazard in place, because the hazard is not that the words were English. It is
that two modules held opinions about the output language and neither knew what the other had
decided. `language.py` decided one thing; `render_text.py` held a hardcoded opinion that could never
be wrong because it was never consulted. A document came out half in each. That is a *coupling*
failure wearing an i18n costume, and the shape above is chosen so the same failure cannot come back
quietly: one module decides (`language.py`), one module holds the translations (`headings.py`), the
renderer only looks things up, and B1's AST scan fails the build the moment a fourth English word
appears in the renderer.

Three ideas worth carrying out of this slice:

- **"Consistent with the last feature" is a question, not an answer.** Spec 002 landed a genuinely
  good pattern — versioned YAML plus a pydantic loader — and the reflex is to reuse it. But that
  pattern solves "someone who is not editing code needs to extend this list". Headings fail that
  test: you cannot add a language without editing Python, so data-in-YAML would only give you two
  files that can disagree. Reuse the *reasoning* behind a pattern, not its shape.
- **A "before" invariant needs a different kind of sensor than a "must not import" invariant.**
  Spec 002's AST scan proves ingestion never imports `anthropic`. No AST scan can prove the LLM is
  called *after* the language gate — ordering is behaviour, so its sensor has to run the code and
  watch what does not happen. Hence the exploding `Rephraser` rather than a fourth import scan.
- **A failure you cannot reach is still worth writing.** `section_headings()` raising on an unknown
  language is unreachable once AC-001 holds. Writing it anyway turns an invariant that lives in
  someone's head ("`cv.language` is always one of the four") into one the program states out loud —
  and if AC-001 ever regresses, the tool refuses to render instead of quietly shipping a
  half-English CV. Which is L-003 exactly: a refusal is this application working.
