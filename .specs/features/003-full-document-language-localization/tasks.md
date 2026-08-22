# Tasks: 003-full-document-language-localization

- **Spec:** `.specs/features/003-full-document-language-localization/spec.md`
- **Status:** planning

<!--
Every task is atomic: one deliverable, independently verifiable, independently committable,
one commit. Every task traces to at least one AC-NNN, or it should not exist.
Validate with: python scripts/validate_tasks.py .specs/features/003-full-document-language-localization/tasks.md
-->

## Gate commands

| Level | Runs | Use when the task… |
|---|---|---|
| `quick` | ruff + unit tests | touches unit-tested code only |
| `full` | ruff + unit + integration + e2e | touches integration or e2e behaviour |
| `build` | full + architectural boundary checks | is the last task in a phase, or touches no tests (config, wiring) |

Run as `python scripts/gate.py <level>`. Non-zero exit means STOP and fix. Never lower a task's
gate level to make it pass.

## Phase 1 — `language.py`: the capability gate and its reason codes

Order matters here. T-001 lands *before* anything in this phase can turn the existing French
proficiency test red, so the fixture move is visibly a deliberate prep step in its own commit,
not a fix bundled into the commit that broke it (design concern 1). T-002 (the `reason_code`
field) lands before T-003 (the gate that needs a `LanguageRefusal.UNSUPPORTED_LANGUAGE` member to
return) so the model shape exists before code returns it.

- [x] **T-001** — Re-arrange the proficiency-vocabulary regression test onto a supported language
  - **Covers:** AC-001
  - **Files:** `tests/unit/generation/test_language.py`
  - **Gate:** quick
  - **Done when:** `test_a_proficiency_level_recognized_by_matching_is_also_recognized_by_generation`
    builds its profile with `Language(name="German", proficiency="advanced")` and calls
    `resolve_output_language(..., override="german")`, asserting `allowed is True`; no other test
    in the file changes; `python scripts/gate.py quick` exits 0 with the test still passing (it
    passes today under French for the same reason it will pass under German, proficiency
    vocabulary, not language support, so this commit changes no behaviour, only the vehicle).
    The commit message states this is a pre-emptive rearrangement ahead of AC-001's
    `SUPPORTED_LANGUAGES` gate (design concern 1), which would otherwise make this test's French
    fixture fail for an unrelated reason (French is not, and will not become, supported) and make
    the later fix look like the implementer edited a test to force a gate green.

- [x] **T-002** — Add `LanguageRefusal` and a `reason_code` field on `LanguageResolution`
  - **Covers:** AC-007
  - **Files:** `src/cv_writer/generation/language.py`, `tests/unit/generation/test_language.py`
  - **Gate:** quick
  - **Done when:** two new failing tests (added first) assert, for a profile with no German
    entry, `resolve_output_language(..., override="german").reason_code ==
    LanguageRefusal.NOT_IN_PROFILE`, and for a profile listing German at `"basic"`,
    `== LanguageRefusal.BELOW_WORKING_PROFICIENCY`. Both fixtures use German deliberately:
    German is in `SUPPORTED_LANGUAGES`, so these two tests stay green when T-003 puts the
    capability gate *ahead* of the profile check. A fixture on an unsupported language would
    pass here and flip to `UNSUPPORTED_LANGUAGE` one task later, turning T-002's own tests red
    inside T-003's commit. They go green once `LanguageRefusal(str, Enum)` (three members:
    `UNSUPPORTED_LANGUAGE`, `NOT_IN_PROFILE`, `BELOW_WORKING_PROFICIENCY`) is added,
    `_check_profile_supports()` returns the matching member alongside its existing
    `(bool, reason)` pair, `LanguageResolution.reason_code: LanguageRefusal | None = None` is
    added, **and** `resolve_output_language()`'s single `LanguageResolution(...)` construction
    (`language.py:169` today) passes that member through. That call site must change: it is the
    only construction site in `src/`, so leaving it alone means `reason_code` is `None` on every
    refusal and AC-007 cannot be discharged (contract C-003 — an earlier draft of this task and
    of C-003 forbade exactly the edit the criterion requires). The field defaults to `None` so
    no *other* construction site would need changing; there is no other one today. The prose
    `reason` stays populated alongside `reason_code` — `generation/pipeline.py:52` reads it and
    `draft.html.jinja:69` renders it, so it is added to, not replaced. Assert
    `len(LanguageRefusal) == 3` rather than that the members are pairwise unequal: distinct
    `Enum` members are unequal by construction, so that assertion tests `enum.Enum` and not this
    module (`.specs/LESSONS.md` L-007). The real discrimination is that these two tests plus
    T-003's pin three different members from three different fixtures, so no single hardcoded
    `reason_code` satisfies them all. `python scripts/gate.py quick` exits 0.

- [x] **T-003** — Gate `resolve_output_language()` on `SUPPORTED_LANGUAGES` before the profile check
  - **Covers:** AC-001, AC-007
  - **Files:** `src/cv_writer/generation/language.py`, `tests/unit/generation/test_language.py`
  - **Gate:** quick
  - **Done when:** failing tests are added first (both use a profile whose only language is
    French at "professional", a language a shipped `data/profile.yaml` no longer makes
    unreachable now that AC-002 will add Spanish as the fourth supported language, per design
    concern 5; French stays unsupported so the refusal is reachable) asserting: (1)
    `resolve_output_language(..., override="french")` returns `allowed is False` and
    `reason_code == LanguageRefusal.UNSUPPORTED_LANGUAGE`, distinct from the reason the profile
    check would have given for the same French-at-professional profile if the gate were absent
    (proving capability is checked, not permission); (2) a posting whose `detect_posting_language()`
    resolves to "unknown" (zero stopword hits, no override) is refused with
    `reason_code == LanguageRefusal.UNSUPPORTED_LANGUAGE`, not the old "not listed in the profile's
    languages" text. Both go green once `resolve_output_language()` gains the early return: after
    the override/detect fork, before `_resolve_pt_variant()` and before
    `_check_profile_supports()`, returning `LanguageResolution(allowed=False,
    reason_code=LanguageRefusal.UNSUPPORTED_LANGUAGE, ...)` when the resolved language is not in
    `SUPPORTED_LANGUAGES`. All pre-existing tests in the file (including T-001's rearranged one)
    stay green. `python scripts/gate.py quick` exits 0.

- [x] **T-004** — Add Spanish to `SUPPORTED_LANGUAGES`, disjoint from the other three
  - **Covers:** AC-002
  - **Files:** `src/cv_writer/generation/language.py`, `tests/unit/generation/test_language.py`
  - **Gate:** quick
  - **Done when:** failing tests are added first: a Spanish posting (built from Spanish-only
    vocabulary not present in the Portuguese set, per design decision 5, avoiding words like
    "para", "com", "somos" and "candidato") is detected as "spanish"; `resolve_output_language()`
    on a Spanish posting with no `country` set returns `variant is None` (no PT-PT/PT-BR mechanism
    applies); a parametrized test asserts `SUPPORTED_LANGUAGES["spanish"]` is disjoint (empty set
    intersection) from each of `SUPPORTED_LANGUAGES["english"]`, `["portuguese"]`, `["german"]` in
    turn. All three go green once a curated Spanish stopword set is added to
    `SUPPORTED_LANGUAGES`. The pre-existing "team" overlap between English and German is left
    untouched, no test asserts English/German/Portuguese are mutually disjoint, only that Spanish
    is disjoint from each. `python scripts/gate.py quick` exits 0.

- [x] **T-005** — Parametrize the profile-proficiency gate over all four supported languages
  - **Covers:** AC-003
  - **Files:** `tests/unit/generation/test_language.py`
  - **Gate:** build
  - **Done when:** one parametrized test body (four ids: english, portuguese, german, spanish)
    builds a profile whose only language entry is that language at a proficiency string whose
    rank equals `MINIMUM_WORKING_RANK`, and asserts
    `resolve_output_language(..., override=<language>)` is `allowed is True` with
    `reason_code is None`, and a second parametrization (same four ids) puts the language at
    "basic" and asserts `allowed is False` with
    `reason_code == LanguageRefusal.BELOW_WORKING_PROFICIENCY`, proving `_check_profile_supports()`
    applies one gate with no special-casing for Spanish. No production code changes (Spanish
    already went through the same `_check_profile_supports()` path as the other three once T-004
    landed). `python scripts/gate.py build` exits 0.

## Phase 2 — Rendering: headings follow the resolved language

- [x] **T-006** — Add `generation/headings.py`: a language-keyed `SectionHeadings` mapping
  - **Covers:** AC-004
  - **Files:** `src/cv_writer/generation/headings.py`, `tests/unit/generation/test_headings.py`
  - **Gate:** quick
  - **Done when:** a new test file, written first (all red against a nonexistent module),
    asserts: `section_headings("english")` returns exactly `"Experience"`, `"Education"` and
    `"Skills"` — today's rendered output pinned byte-for-byte, so the English CV cannot drift
    while the other three languages are added (contract C-006; nothing else in the suite pins
    these, as the `## Experience` strings elsewhere under `tests/` are hand-written Markdown
    *inputs* to `render_html`/`page_fit`, never assertions on `render_markdown()`'s output);
    `("portuguese")`, `("german")` and `("spanish")` each return non-empty
    `experience`/`education`/`skills` fields, none equal to the corresponding English field;
    `section_headings("English") == section_headings("english")`, because `GeneratedCv.language`
    is a free `str` and a capitalized value must not raise;
    `set(SECTION_HEADINGS) == set(cv_writer.generation.language.SUPPORTED_LANGUAGES)`; and
    `section_headings("french")` raises `ValueError` naming "french" and the supported set (not a
    silent English fallback, design decision 4, `.specs/LESSONS.md` L-004). All pass once
    `headings.py` is added: a frozen `SectionHeadings(BaseModel)`, a `SECTION_HEADINGS: dict[str,
    SectionHeadings]` with one entry per supported language (English/Portuguese/German/Spanish
    headings per the design's draft translations, OQ-2 not yet resolved, translations may need a
    later one-line correction), and `section_headings(language)` normalizing its argument with
    `.strip().lower()` before lookup. The module imports nothing from `cv_writer` (design
    boundary B3). `python scripts/gate.py quick` exits 0.

- [x] **T-007** — `render_markdown()` looks up headings from `cv.language` instead of hardcoding them
  - **Covers:** AC-004
  - **Files:** `src/cv_writer/generation/render_text.py`, `tests/unit/generation/test_render_text.py`
  - **Gate:** quick
  - **Done when:** a new test file (`render_markdown()` has no unit test today), written first,
    is red against the current hardcoded "## Experience"/"## Education"/"## Skills". It builds
    one shared fixture — profile and `GeneratedCv` — whose *profile-authored* content (name,
    email, one `education` entry, one `skills` entry, one accepted bullet) contains none of the
    words "Experience", "Education", "Skills", pinned in the test file rather than imported. It
    has: a parametrized test over all four languages asserting the render contains the line
    `f"## {section_headings(lang).experience}"` and likewise for `.education` and `.skills`; for
    the three non-English ids, an assertion that no line of the render starting with `"## "`
    contains "Experience", "Education" or "Skills" — scoped to heading lines because the
    document also carries profile-authored content the spec keeps verbatim, so an unscoped
    substring check would go red on an English bullet or skill name rather than on a heading
    (contract C-006); and an English regression test asserting the render still contains
    "## Experience", "## Education" and "## Skills" exactly. A separate test asserts
    `render_plain_text()` on a non-English `GeneratedCv` contains each heading word *and* that
    `"## " + heading` is absent — the second half is the one that can actually fail if the
    markers are not stripped, since the first half alone passes on un-stripped Markdown
    (inheritance, not a re-implementation). All go green once `render_markdown()` calls
    `section_headings(cv.language)` and uses its three fields instead of the literal strings.
    `render_markdown(cv, profile)`'s signature is unchanged (design decision 2).
    `python scripts/gate.py quick` exits 0.

- [ ] **T-008** — Architectural sensor: `render_text.py` owns no user-visible words
  - **Covers:** AC-004
  - **Files:** `tests/unit/generation/test_render_text_has_no_hardcoded_headings.py`
  - **Gate:** build
  - **Done when:** an AST scan (modelled on
    `tests/unit/web/test_core_has_no_web_imports.py`) walks every `ast.Constant`/literal
    `ast.JoinedStr` part in `src/cv_writer/generation/render_text.py` (skipping module/function
    docstrings) and fails if any string constant contains two or more consecutive ASCII letters;
    it passes against the module as left by T-007 (every literal is punctuation/whitespace:
    "# ", "## ", " | ", ": ", ", ", "- ", "#", "", "\n"). The test suite includes, same file: a
    synthetic-violation case proving the scan actually catches a planted word, and a guard
    asserting the scan looked at a real, non-empty file (a path typo must not pass trivially).
    `python scripts/gate.py build` exits 0.

## Phase 3 — Amend spec 001's criterion 26

- [ ] **T-009** — Amend criterion 26's ATS bullet and add the dated Revision-log entry, with its sensor
  - **Covers:** AC-005
  - **Files:** `specs/features/001-cv-writer.md`, `tests/unit/scripts/test_spec_001_criterion_26_amendment.py`
  - **Gate:** build
  - **Done when:** the sensor, written first and red against the file's current text, splits
    `specs/features/001-cv-writer.md` once at `### Revision log` into `criteria_part`/`log_part`
    and asserts, comparing against a whitespace-normalized copy of each half (runs of whitespace
    collapsed to single spaces) for the phrase check while keeping the raw text for the
    line-anchored ones: (1) the string "standard section headings (Experience, Education,
    Skills)" is absent from the *normalized* `criteria_part`. Normalization is load-bearing, not
    tidiness: the phrase is line-wrapped in the source today (it breaks after "Education," and
    resumes indented on the next line), so a naive contiguous-substring check is already green
    before the amendment and proves nothing (`.specs/LESSONS.md` L-007). The implementer MUST
    observe this assertion fail against the unamended file before writing the amendment; if it
    passes on the first run, the sensor is wrong, not the file. (2) `criteria_part` still has a
    line matching `^26\. ` and still contains "ATS-safe structure" (the criterion is amended, not deleted, hard rule #1);
    (3) `log_part` has an entry matching `^- \*\*(\d{4}-\d{2}-\d{2})` dated after `2026-08-17`
    whose body mentions both "criterion 26" (case-insensitive) and "003"; (4) the file path exists
    and both halves are non-empty (the scan looked at something real). It goes green once
    criterion 26's bullet is reworded so the parenthetical reads as an illustrative English
    example of the ATS-safe pattern, a small number of clearly-labelled, consistently-named
    sections, rather than a mandate for those English words regardless of output language, and a
    new dated Revision-log entry is added below the 2026-08-17 one, quoting the old wording
    verbatim (never-delete-shaped: the superseded text is preserved in the log, not erased) and
    naming spec 003 and criterion 26. `python scripts/gate.py build` exits 0.

## Phase 4 — AC-006: the refusal reaches the user before any model call

- [ ] **T-010** — Prove the LLM is never called for a refused language
  - **Covers:** AC-006
  - **Files:** `tests/integration/generation/test_generation_pipeline.py`
  - **Gate:** full
  - **Done when:** a new test injects a `Rephraser` double whose `rephrase()` raises
    `AssertionError("the LLM was called for a refused language")` into `generate_cv()`, called
    with `language_override` set to an unsupported language against a profile whose only language
    is French at "professional" (same reachability reasoning as T-003, design concern 5); the
    test asserts the return value is a `GenerationFailure` whose `reason` is non-empty, and passes
    only because the double's `rephrase()` never fires (an `AssertionError` from inside it would
    fail the test). No production code changes, this pins the existing early return in
    `generate_cv()` (design boundary B2) as a sensor, not new behaviour.
    `python scripts/gate.py full` exits 0.

- [ ] **T-011** — Prove the refusal reaches the user through the web re-render path
  - **Covers:** AC-006
  - **Files:** `tests/unit/web/test_language_refusal_reaches_the_user.py`
  - **Gate:** build
  - **Done when:** a new test, using FastAPI's `TestClient` over `create_app()` (pattern from
    `tests/unit/web/test_download_guard.py`), creates a draft, POSTs to
    `/drafts/{draft_id}/generate` with `language_override=french` against a profile whose only
    language is French at "professional", and asserts the response status is 422 and the response
    body contains the refusal's `reason` text (the same "reaches the user" claim AC-006 makes,
    exercised through `draft.html.jinja`'s existing `generation_failure.reason` block for the
    first time on this path). `python scripts/gate.py build` exits 0.

## Coverage matrix

Every criterion in the spec appears here, against at least one task. A criterion with no task is
a planning bug, not an acceptable omission.

| Criterion | Task(s) | Test level |
|---|---|---|
| AC-001 | T-001, T-003 | unit |
| AC-002 | T-004 | unit |
| AC-003 | T-005 | unit |
| AC-004 | T-006, T-007, T-008 | unit |
| AC-005 | T-009 | unit (documentation sensor) |
| AC-006 | T-010, T-011 | integration, unit (web) |
| AC-007 | T-002, T-003 | unit |

## Execution notes

Append as you go — what was harder than planned, what got deferred, what the gate caught.
This is the running memory for anyone resuming mid-feature.
