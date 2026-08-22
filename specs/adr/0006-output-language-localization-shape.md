# ADR 0006: Output-language localization shape

- **Status:** accepted
- **Date:** 2026-08-21

## Context

Spec `.specs/features/003-full-document-language-localization/spec.md` (AC-001..AC-006) fixes the
defect the first real end-to-end run produced on 2026-08-19: a CV with English section headings
over Spanish bullet content. Two root causes, both traced in code and both re-verified as still
live on 2026-08-21:

- `generation/render_text.py::render_markdown()` hardcodes `"## Experience"`, `"## Education"` and
  `"## Skills"` (lines 26, 31, 36). Only `cv.accepted_bullets` ever passes through the rephraser
  with a target language; the document's own structural strings are never translated at all.
- `generation/language.py::resolve_output_language()` validates an `override` only against the
  profile's `languages`, never against `SUPPORTED_LANGUAGES` — the set `detect_posting_language()`
  actually knows. An override naming a language the tool has no other support for is allowed
  through so long as the profile lists it at working proficiency.

Five decisions need pinning down before code, three of which are genuinely hard to reverse once
tests exist against them: where the localized strings live and in what format, how the resolved
language reaches the renderer, and what shape a refusal returns. ADR 0004 decision 8 established
the current `language.py` design and is amended, not replaced, by decision 3 below.

Spec 002 landed a versioned-YAML-plus-pydantic-loader pattern for curated lists
(`ingestion/term_list.py`, `ingestion/data/requirement_terms.yaml`), itself modelled on ADR 0004
decision 6's `generation/data/pt_pt_terms.yaml`. Whether the heading translations should follow it
is decision 1, and it is the decision most worth reading.

## Decisions

### 1. The localized structural strings live in code, in a new `generation/headings.py` — not in YAML

A new module holding a mapping from the resolved language to a small named model:

```python
class SectionHeadings(BaseModel):        # frozen
    experience: str
    education: str
    skills: str

SECTION_HEADINGS: dict[str, SectionHeadings] = {...}   # one entry per SUPPORTED_LANGUAGES key

def section_headings(language: str) -> SectionHeadings: ...
```

Three headings times four languages is twelve strings, and the honest question is what a data file
would buy for them.

**Rejected: a versioned YAML file plus a pydantic loader, mirroring `requirement_terms.yaml`.**
This is the "consistent with the last feature" answer and it is the wrong one, for a reason worth
naming precisely. `term_list.py`'s own docstring says why that pattern exists: *"Vocabulary that
lives in code gets extended by whoever is editing code; vocabulary that lives in data gets extended
by whoever hit the gap."* The requirement vocabulary is open-ended, extended reactively by the
maintainer who just watched a posting extract one requirement, and — critically — extending it is a
*pure data change*: add a phrase, bump `version`, done, no Python touched.

None of that holds for headings. The set is closed (OQ-5 established that these three are all the
structural strings `render_text.py` emits, and a fourth section would arrive with its own
criterion). It is not extended reactively — a heading is added exactly when a language is added.
And adding a language is *irreducibly a code change*: `SUPPORTED_LANGUAGES` is a Python dict of
curated stopword sets, so "support Spanish" already means editing `language.py`. A YAML file would
therefore split one atomic change across two files in two formats, and introduce a failure mode
that does not exist today — `SUPPORTED_LANGUAGES` and the heading file disagreeing, with nothing
but a test standing between that and a `KeyError` at render time. The version field would be
ceremony: a version number is useful when data and code ship on different clocks, and here they
cannot.

The one real argument for YAML is OQ-2 — the translations are AI-drafted and want a native-speaker
read, and a reviewer may find YAML friendlier than Python. It is not enough: a dict of quoted
strings with named fields reads as easily as YAML in a diff, and the reviewer is reading a diff
either way.

**Rejected: a bare `dict[str, dict[str, str]]` inside `render_text.py`.** Fewest files, but it puts
the words back in the module whose job is layout, which is what boundary B1 in the design exists to
prevent, and it hides the pairing between the heading table and `SUPPORTED_LANGUAGES` inside a
rendering module.

**Rejected: `gettext` / `.po` catalogues, or `babel`.** The standard answer for application
localization, and enormously more machinery than twelve strings justify: a new dependency, an
extraction step, compiled `.mo` artifacts in the repo, and a locale-negotiation model this tool
does not need because it already resolves exactly one language per document, by its own rules. If
the localized surface ever grows past the CV artifact — the spec's "Out of scope" explicitly keeps
the web UI's English chrome out of this slice — this decision is worth revisiting, and it is cheap
to revisit: `section_headings()` is the only entry point that would change.

**Named fields rather than string keys** (`headings.experience`, not `headings["experience"]`):
a missing or misspelled field is then a pydantic validation error at import time rather than a
`KeyError` during a render, and adding a fourth section becomes a model change every language entry
must answer for.

**Completeness is a test, not an import-time assert.** `set(SECTION_HEADINGS) ==
set(SUPPORTED_LANGUAGES)` is asserted by a unit test that imports both modules, rather than by an
`assert` at module scope. An import-time assert in library code fails at import of any consumer,
including tooling that only wanted to read a docstring; and this repo's stated posture is that a
task is done when a sensor exits zero, which is what a test is. The cost is that the failure
arrives at test time rather than import time — acceptable, since the two dicts can only be edited
together by a human who will run the gate.

### 2. `render_markdown()` reads `cv.language`; its signature does not change

`GeneratedCv.language` already carries the resolved language, and this was verified at every call
site rather than assumed:

- `pipeline.py::generate_cv()` is the only place a `GeneratedCv` is constructed, and it sets
  `language=language_resolution.detected` — the same value passed to
  `RephraseRequest.target_language`, so bullets and headings cannot disagree.
- `generation/write_output.py:59` calls `render_markdown(cv, profile)` on that object.
- `web/routes.py:110` calls `render_markdown(narrowed, profile)`, where `_narrow_cv` (`routes.py:99`)
  copies `language=cv.language` through unchanged. There is no third call site.

**Rejected: adding a `language: str` parameter.** The value is already on the object being passed.
A parameter creates two sources of truth for one fact, and this codebase already has a live example
of how that goes wrong: `render_html(markdown_text, language=cv.language, title=...)` takes the
language separately from the Markdown it renders, and nothing prevents a caller passing one
document's text with another's language. Copying that shape into a second renderer doubles the
surface for the same class of bug this ADR exists to fix.

**Rejected: injecting a `SectionHeadings` at the call site.** Maximally testable and explicit, but
it moves "which language is this document in" out of the pipeline that decided it and into every
caller of the renderer, including the page-fit measurement loop in the web layer. That is the
coupling failure again, just relocated.

### 3. The `SUPPORTED_LANGUAGES` gate runs before the profile check, and refusals carry a reason code

`resolve_output_language()` gains an early return, placed *after* the override/detect fork and
*before* both `_resolve_pt_variant()` and `_check_profile_supports()`. It is checked against the
**resolved** language, whether that came from an override or from detection.

The ordering is the substance of AC-001. Both checks can fail for the same input, and they answer
different questions — "can this tool write in it" versus "can this person write in it" — with
different remedies. Reporting the profile answer first sends the user to edit `data/profile.yaml`,
after which the tool would still emit an English-headed document. Capability before permission.

Gating the *resolved* language rather than only the override is a deliberate superset of AC-001's
literal text: it also catches `detect_posting_language()`'s `"unknown"` sentinel, which today is
refused with "not listed in the profile's languages" — a true statement and the wrong explanation.
It is what makes AC-006's broader phrasing ("a language absent from `SUPPORTED_LANGUAGES`") true as
written. Flagged in `design.md` as a spec-precision note for the human rather than made silently.

`LanguageResolution` gains `reason_code: LanguageRefusal | None = None`, where `LanguageRefusal` is
a `str`-valued `Enum` (same idiom as `generation/models.py::ExtraInputKind`) with exactly three
members: `UNSUPPORTED_LANGUAGE`, `NOT_IN_PROFILE`, `BELOW_WORKING_PROFICIENCY`. `reason` keeps its
current job — the human-readable sentence that reaches the UI through `GenerationFailure.reason`.

**Rejected: three distinct prose strings and nothing else.** This is what the codebase does
everywhere else (`IngestionFailure.reason`, `GenerationFailure.reason`, `ValidationFailure.reason`),
and consistency is a real cost of deviating. But AC-001's requirement is literally that the new
reason be *distinct from* two named others, and distinctness between sentences can only be asserted
by pinning the sentences — after which every improvement to the wording is a test failure, and the
tempting fix is to loosen the assertion. An enum makes distinctness a property of the type: three
members, `!=` each other, prose free to change. The deviation is confined to one model in one
module and nothing downstream branches on it today.

**Rejected: raising a distinct exception per refusal kind.** `generate_cv()`'s docstring promises it
"never raises on a 'normal' rejection" and returns `GenerationFailure` instead, mirroring
`ingestion/models.py`'s result-vs-failure pattern. A language refusal is the most normal rejection
this pipeline has.

### 4. An unknown language at render time raises; it never falls back to English

`section_headings(language)` raises `ValueError` naming the language and the supported set. It does
not `dict.get(..., ENGLISH)`.

**Rejected: falling back to English.** That behaviour *is* the defect. A fallback would reproduce
the 2026-08-19 artifact — Spanish bullets under English headings — while every test stayed green,
and it would do so exactly in the case where something upstream had already gone wrong. `.specs/LESSONS.md`
L-004 is the general form: prefer a loud failure to a quiet, plausible-looking empty-or-wrong
result. L-003 is the specific form: a refusal is this application working correctly.

Once AC-001 holds, this raise is unreachable through `generate_cv()`, because no `GeneratedCv` can
be constructed with a language outside `SUPPORTED_LANGUAGES`. That is the point rather than an
objection: the raise is the executable statement of an invariant that would otherwise live only in
a reviewer's head, and it is what converts a future regression in `language.py` from a silently
half-translated PDF into a refusal.

### 5. Spanish joins `SUPPORTED_LANGUAGES` with a stopword set disjoint from the other three

AC-002 adds Spanish as a fourth flat language with no variant mechanism (`_resolve_pt_variant()`
stays Portuguese-only, and a Spanish resolution carries `variant=None`).

`detect_posting_language()` scores by raw set intersection (`len(words & stopwords)`) and resolves a
tie with `max()`, which returns the first key at the maximum in dict insertion order. A word present
in two languages' sets therefore inflates both scores equally and hands the outcome to whichever
language was written into the dict first. Spanish and Portuguese share far more high-frequency
vocabulary than any pair already in the set, so the Spanish entry must avoid words already claimed
by another language — `para`, `com`, `somos` and `candidato` are the obvious traps against the
existing Portuguese set, and `experiencia`/`experiência` and `equipo`/`equipa` are safe precisely
because the accent and the ending make them different strings. A unit test asserts the Spanish set
is disjoint from each of the other three.

**Rejected: reworking the scorer** (ratio normalisation, per-language weights, or honouring
`confidence` in `resolve_output_language()`). No criterion in spec 003 asks for it, and it would
change detection behaviour for the three existing languages as a side effect of adding a fourth.

**Rejected: removing `"team"` from the English or German set** to make disjointness a universal
invariant instead of a Spanish-only one. It is a pre-existing overlap, removing curated data is not
this slice's business, and the narrower test — Spanish against each of the others — is honest about
what it actually guarantees. The overlap is documented in the test rather than quietly tolerated.

## New runtime dependencies

None. `headings.py` uses `pydantic`, already a core dependency; no YAML file, so no new loader and
no new parse path.

## Consequences

- One new production module (`generation/headings.py`), one changed renderer, one changed resolver.
  `pipeline.py`, `routes.py` and `draft.html.jinja` are untouched: AC-006 is discharged by the
  early return that already exists, plus a sensor that pins it.
- `tests/unit/generation/test_language.py::test_a_proficiency_level_recognized_by_matching_is_also_recognized_by_generation`
  goes red under decision 3 — it uses **French** at `"advanced"` as its vehicle for asserting that
  matching and generation share one proficiency vocabulary, and French is not in
  `SUPPORTED_LANGUAGES`. The test must be re-arranged onto a supported language (German at
  `"advanced"`), not deleted or weakened; the invariant it protects is real and was itself the fix
  for a past drift between the two packages.
- `render_text.py` acquires an architectural test (`design.md` boundary B1): no string literal in
  that module may contain two or more consecutive ASCII letters. Adding any user-visible word there
  later fails the build, which is the enforcement of OQ-5's promise that a fourth section arrives
  with its own criterion.
- `LanguageResolution` gains a field. Nothing outside `generation/language.py` constructs one, and
  the field defaults to `None`, so no existing caller changes.
- Adding a fifth language remains a three-place edit — a stopword set in `language.py`, a
  `SectionHeadings` entry in `headings.py`, and the expected values in one parametrized test — with
  a test that fails if the first two disagree. That is deliberately not a data-only change, per
  decision 1.
- The HTML `lang` attribute will now receive `"spanish"` alongside `"english"`/`"portuguese"`, none
  of which is valid BCP-47. Pre-existing, tracked as the spec's OQ-3, explicitly out of scope here.
- The translations ship AI-drafted and native-speaker-unreviewed (OQ-2), the same caveat spec 001
  already carries for PT-PT. Decision 1 makes correcting one a one-line edit plus one expected
  value.
