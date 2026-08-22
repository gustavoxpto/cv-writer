# Contract: 003-full-document-language-localization

- **Spec:** `.specs/features/003-full-document-language-localization/spec.md`
- **Implementer:** `implementer`
- **Verifier:** `verifier`
- **Date:** 2026-08-21

<!--
The contract is written by the IMPLEMENTER before any code exists, and signed by the VERIFIER
after checking it against the spec. It is the agreed checklist both sides work from.

Why it exists — two failures it prevents:
  1. Work slipping through. The verifier walks this list item by item, so nothing is silently
     skipped and nothing is silently declared done.
  2. Verifier drift. Without an agreed list, a verifier starts proposing unrelated improvements
     and the implementer chases them forever. The contract bounds what "done" means.

Validate with: python scripts/validate_contract.py .specs/features/003-full-document-language-localization
-->

## Signature

- [x] **Verifier has checked this list against `spec.md`** and confirms it covers every
      acceptance criterion, adds nothing outside the spec, and that each **Check** below is
      something a sensor or an inspection can actually decide. — verifier, 2026-08-22.
      Re-checked the full list after the prior UNSIGNED pass; C-003 no longer forbids editing
      the single `LanguageResolution(...)` construction site (`language.py:169`) and its three
      refusal fixtures each isolate exactly one refusal cause, given AC-001's ordering; C-006's
      negative heading assertion is scoped to `"## "`-prefixed lines so profile-authored
      content cannot turn it red, pins today's exact English headings, and its
      `render_plain_text()` check can fail on unstripped Markdown markers. AC-001..AC-007 are
      each covered by at least one contract item, and the "Explicitly not in this contract"
      list matches the spec's Out of scope one-to-one.

*(Execute does not start until this box is checked. Anything the verifier wants that is not on
this list must go back into the spec first — it does not get added at validation time.)*

## What will be built

Each item is one observable outcome. Not a task, not a file — an outcome someone else can check.

- [x] **C-001** — Requesting generation with an `override` naming a language absent from
  `SUPPORTED_LANGUAGES` is refused, and the refusal fires before the profile-proficiency check
  and before PT-variant resolution, for a language a shipped profile can genuinely still name
  (French).
  - **Verifies:** AC-001
  - **Check:** In `tests/unit/generation/test_language.py`, a test builds a `Profile` whose only
    `languages` entry is `Language(name="French", proficiency="professional")` and a `Posting`,
    then asserts `resolve_output_language(posting, profile, override="french").allowed is False`.
    Read `src/cv_writer/generation/language.py::resolve_output_language()` and confirm the
    `if language not in SUPPORTED_LANGUAGES:` early return appears in the function body *before*
    the calls to `_resolve_pt_variant()` and `_check_profile_supports()` — i.e. the refusal is
    reachable without either of those running (capability checked before permission, per design
    decision 3). `python scripts/gate.py quick` exits 0.

- [x] **C-002** — A posting `detect_posting_language()` resolves to `"unknown"` (zero stopword
  hits, no override supplied) is refused through the same `SUPPORTED_LANGUAGES` gate as an
  unsupported override, not through the pre-existing "not listed in the profile's languages"
  path.
  - **Verifies:** AC-001
  - **Check:** In `tests/unit/generation/test_language.py`, a test builds a `Posting` whose
    `raw_text` contains no stopword from any `SUPPORTED_LANGUAGES` set, calls
    `resolve_output_language(posting, profile)` with no `override`, and asserts
    `reason_code == LanguageRefusal.UNSUPPORTED_LANGUAGE` (not `NOT_IN_PROFILE`).
    `python scripts/gate.py quick` exits 0.

- [x] **C-003** — A refused `LanguageResolution` carries a machine-readable `reason_code`
  identifying which of the three refusal causes applied, and the three causes are
  distinguishable without asserting on prose, while the existing prose `reason` stays
  populated for the callers that already render it.
  - **Verifies:** AC-007
  - **Check:** In `src/cv_writer/generation/language.py`, confirm `LanguageRefusal` is a
    `str`-valued `Enum` with exactly three members — `UNSUPPORTED_LANGUAGE`, `NOT_IN_PROFILE`,
    `BELOW_WORKING_PROFICIENCY` — and that `LanguageResolution` has a field
    `reason_code: LanguageRefusal | None = None`. Confirm the single site that constructs
    `LanguageResolution(...)` (the return of `resolve_output_language()`, `language.py:169`
    today) supplies `reason_code` on every return path, and that `reason_code is None` holds
    exactly when `allowed is True`. Confirm the prose `reason` field is still populated on
    every refusal alongside `reason_code` — `generation/pipeline.py:52` reads
    `language_resolution.reason` and `draft.html.jinja:69` renders it, so it is not being
    replaced. In `tests/unit/generation/test_language.py`, three refusal tests, each arranged
    so only one cause can fire: (1) `override="french"` against a profile listing French at
    `"professional"` — the profile *would* permit it, so only the `SUPPORTED_LANGUAGES` gate
    can refuse — asserts `reason_code == LanguageRefusal.UNSUPPORTED_LANGUAGE`;
    (2) `override="german"` — in `SUPPORTED_LANGUAGES` — against a profile with no German
    entry asserts `== LanguageRefusal.NOT_IN_PROFILE`; (3) `override="german"` against a
    profile listing German at `"basic"` asserts `== LanguageRefusal.BELOW_WORKING_PROFICIENCY`.
    Each also asserts `allowed is False`. A fourth test asserts an allowed resolution has
    `reason_code is None`. Because the three fixtures differ only in the override/profile pair
    and each pins a different member, no single hardcoded `reason_code` passes all three —
    that is the discrimination, and it replaces asserting the members are pairwise `!=` (which
    tests `enum.Enum`'s semantics, not this module); assert `len(LanguageRefusal) == 3`
    instead. `python scripts/gate.py quick` exits 0.

- [x] **C-004** — Spanish is a supported language: detected the same flat way as the other three,
  with no PT-PT/PT-BR-style variant, and its stopword set shares no member with English's,
  Portuguese's or German's.
  - **Verifies:** AC-002
  - **Check:** In `src/cv_writer/generation/language.py`, confirm `SUPPORTED_LANGUAGES["spanish"]`
    exists as a `set[str]`. In `tests/unit/generation/test_language.py`: a test builds a Spanish
    posting from vocabulary not in the Portuguese set (avoiding `"para"`, `"com"`, `"somos"`,
    `"candidato"`) and asserts `detect_posting_language(...).language == "spanish"`; a test asserts
    `resolve_output_language(spanish_posting, profile).variant is None` for a posting with no
    `country` set; a parametrized test asserts
    `SUPPORTED_LANGUAGES["spanish"] & SUPPORTED_LANGUAGES[lang] == set()` for each of
    `"english"`, `"portuguese"`, `"german"` in turn. `python scripts/gate.py quick` exits 0.

- [x] **C-005** — The profile-proficiency gate (`_check_profile_supports()` against
  `MINIMUM_WORKING_RANK`) applies identically to Spanish as to the other three supported
  languages, with no special-casing in the production code.
  - **Verifies:** AC-003
  - **Check:** In `tests/unit/generation/test_language.py`, one parametrized test body with four
    ids (`english`, `portuguese`, `german`, `spanish`) asserts, for a profile whose only language
    entry is that language at a proficiency whose rank equals `MINIMUM_WORKING_RANK`,
    `resolve_output_language(..., override=<language>).allowed is True` and `reason_code is None`;
    and a second parametrization (same four ids) with the language at `"basic"` asserts
    `allowed is False` and `reason_code == LanguageRefusal.BELOW_WORKING_PROFICIENCY`. Confirm
    `src/cv_writer/generation/language.py::_check_profile_supports()` has no `if language ==
    "spanish"` (or equivalent) branch. `python scripts/gate.py build` exits 0.

- [x] **C-006** — A CV rendered with a given `cv.language` carries that language's experience,
  education and skills section headings; no non-English render emits an English heading; the
  English render is byte-for-byte what it emits today; and `render_plain_text()` carries the
  non-English headings through with Markdown markers stripped.
  - **Verifies:** AC-004
  - **Check:** `src/cv_writer/generation/headings.py` exists, exporting a frozen
    `SectionHeadings(BaseModel)` with `experience`/`education`/`skills` string fields, a
    `SECTION_HEADINGS: dict[str, SectionHeadings]` with one entry per
    `cv_writer.generation.language.SUPPORTED_LANGUAGES` key, and `section_headings(language)`
    which normalizes its argument with `.strip().lower()` before lookup (`GeneratedCv.language`
    is a free `str`, so a capitalized value must not raise) and raises `ValueError` for an
    unknown key. `tests/unit/generation/test_headings.py` asserts: `section_headings("english")`
    returns exactly `"Experience"`, `"Education"`, `"Skills"` — pinning today's output so the
    English CV cannot drift while the other three are added; `("portuguese")`, `("german")`,
    `("spanish")` each return three non-empty fields, none of them equal to the corresponding
    English field; `section_headings("English")` equals `section_headings("english")`;
    `set(SECTION_HEADINGS) == set(SUPPORTED_LANGUAGES)`; and `section_headings("french")` raises
    `ValueError` whose message names `"french"` and the supported set. In
    `src/cv_writer/generation/render_text.py`, confirm `render_markdown()` calls
    `section_headings(cv.language)` and its `(cv, profile)` signature is unchanged from today.
    `tests/unit/generation/test_render_text.py` (new) builds one shared fixture — profile and
    `GeneratedCv` — whose *profile-authored* content (name, email, one `education` entry, one
    `skills` entry, one accepted bullet) contains none of the words `"Experience"`,
    `"Education"`, `"Skills"`, so the negative assertion below can only be about headings; the
    fixture is pinned in the test file, not imported. It has: a parametrized test over all four
    languages asserting the rendered Markdown contains the line
    `f"## {section_headings(lang).experience}"` and likewise for `.education` and `.skills`; for
    the three non-English ids, an assertion that no line of the render starting with `"## "`
    contains `"Experience"`, `"Education"` or `"Skills"` — scoped to heading lines, because the
    document also carries profile-authored content the spec keeps verbatim and an unscoped
    substring check would go red on an English bullet or skill name rather than on a heading;
    and an English regression test asserting the render still contains `"## Experience"`,
    `"## Education"` and `"## Skills"` exactly. A separate test asserts `render_plain_text()` on
    a non-English `GeneratedCv` contains each heading word *and* that `"## " + heading` is
    absent — the second half is what makes the test fail if the markers are not stripped, since
    the first half alone passes on the un-stripped Markdown. `python scripts/gate.py quick`
    exits 0.

- [x] **C-007** — `render_text.py` contains no user-visible word of its own — every heading
  string a reader of the CV would see comes from `headings.py` — and this is enforced by a build
  sensor rather than left to reviewer attention.
  - **Verifies:** AC-004
  - **Check:** `tests/unit/generation/test_render_text_has_no_hardcoded_headings.py` (new) parses
    `src/cv_writer/generation/render_text.py` with `ast.parse`, walks every `ast.Constant` and the
    literal parts of every `ast.JoinedStr` (skipping module/function docstrings), and fails if any
    string constant contains two or more consecutive ASCII letters; run it and confirm it passes
    against the module as changed by C-006 (every remaining literal is punctuation or whitespace:
    `"# "`, `"## "`, `" | "`, `": "`, `", "`, `"- "`, `"#"`, `""`, `"\n"`). The same test file
    includes a synthetic-violation case (a planted literal containing a word) proving the scan
    actually catches what it claims to, and a guard asserting the scan looked at a real,
    non-empty file. `python scripts/gate.py build` exits 0.

- [x] **C-008** — Spec 001's criterion 26 no longer reads as a mandate for the literal English
  words "Experience", "Education", "Skills" regardless of output language, the criterion itself
  still exists (amended, not deleted), and the amendment is recorded as a dated entry in that
  spec's own Revision log.
  - **Verifies:** AC-005
  - **Check:** `tests/unit/scripts/test_spec_001_criterion_26_amendment.py` (new) reads
    `specs/features/001-cv-writer.md` as text, splits it once at `### Revision log` into
    `criteria_part`/`log_part`, and asserts: (1) with runs of whitespace in `criteria_part`
    collapsed to single spaces, the normalized string `"standard section headings (Experience,
    Education, Skills)"` is absent — normalization is load-bearing because the phrase is
    line-wrapped in the source today, so a raw contiguous-substring check is already green before
    any amendment and proves nothing; the verifier confirms the test file actually normalizes
    whitespace before this comparison, not merely on the raw text; (2) `criteria_part` still
    contains a line matching `^26\. ` and still contains the substring `"ATS-safe structure"`
    (criterion 26 amended, not removed); (3) `log_part` contains at least one entry matching
    `^- \*\*(\d{4}-\d{2}-\d{2})` dated later than `2026-08-17` whose body mentions both
    `"criterion 26"` (case-insensitive) and `"003"`; (4) the file path exists and both halves are
    non-empty. `python scripts/gate.py build` exits 0.

- [x] **C-009** — Generation requested for a language absent from `SUPPORTED_LANGUAGES` never
  reaches the `Rephraser`, and returns a `GenerationFailure` carrying a non-empty reason.
  - **Verifies:** AC-006
  - **Check:** In `tests/integration/generation/test_generation_pipeline.py`, a new test defines a
    `Rephraser` double whose `rephrase()` raises `AssertionError("the LLM was called for a
    refused language")`, calls `generate_cv()` with that double injected and
    `language_override` set to `"french"` against a profile whose only language is French at
    `"professional"`, and asserts the return value is a `GenerationFailure` with a non-empty
    `.reason`. The test must pass because the double's `rephrase()` never fires — an
    `AssertionError` raised from inside it would fail the test rather than being swallowed.
    `python scripts/gate.py full` exits 0.

- [x] **C-010** — When a user submits a generation request for a refused language through the
  web UI, the HTTP response reports the refusal (422) with the reason text visible in the
  response body, without a server error.
  - **Verifies:** AC-006
  - **Check:** `tests/unit/web/test_language_refusal_reaches_the_user.py` (new), using FastAPI's
    `TestClient` over `create_app()` (pattern from `tests/unit/web/test_download_guard.py`):
    create a draft against a profile whose only language is French at `"professional"`, POST to
    `/drafts/{draft_id}/generate` with `language_override=french`, and assert
    `response.status_code == 422` and the refusal's reason text appears in `response.text` (the
    `generation_failure.reason` block in `draft.html.jinja`). `python scripts/gate.py build`
    exits 0.

## Explicitly not in this contract

Things the implementer will *not* do, so the verifier does not raise them as gaps. If one of
these turns out to matter, it becomes a new criterion in the spec, not a surprise at validation.

- Reworking `detect_posting_language()`'s scoring, or making `resolve_output_language()` act on
  its `confidence` field. Design concern 2 flags the risk (Spanish/Portuguese near-ties resolved
  by dict insertion order) but no criterion here asks for it.
- A native-speaker review of the draft heading translations (OQ-2, non-blocking, open). The
  Portuguese/German/Spanish strings in `headings.py` ship as an AI-drafted best effort.
- Changing `render_html.py`'s `language` value to a BCP-47 code (OQ-3, non-blocking, open).
  `lang="spanish"` remains invalid BCP-47 after this slice, same as `"english"`/`"portuguese"`
  today.
- Any change to `render_html.py` beyond what already receives `cv.language` unchanged at both
  call sites (spec's Out of scope).
- The numeric-formatting false rejection in `generation/validator.py` (locale spacing on
  percentages) — carried over from spec 002's out-of-scope list, its own spec.
- The preferred-vs-required language bug ("Se valorará: alemán" reported as required) — a real,
  adjacent defect named in the spec's Out of scope, not covered by any criterion here.
- Translating profile-authored content — `education[].degree`, `.institution`,
  `skills[].name`. These stay verbatim (resolved at the 2026-08-19 sign-off, OQ-1).
- A PT-PT/PT-BR-style variant mechanism for Spanish. Spanish is one flat language;
  `_resolve_pt_variant()` stays Portuguese-only.
- Adding Spanish to `data/profile.example.yaml`. No criterion asks for it.
- Any change to `pt_pt_checker.py`, `validator.py`, or `web/templates/` beyond the existing
  `generation_failure.reason` block C-010 exercises for the first time on this path.
