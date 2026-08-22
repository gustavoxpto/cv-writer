# Validation: 003-full-document-language-localization

- **Verdict:** PASS
- **Verifier:** `verifier` (independent of the `implementer` session — hard rule #5)
- **Date:** 2026-08-22
- **Commit range:** `4e37006..667f220`
- **Iteration:** 1 of max 3

## Score

| Check | Score | Minimum to pass | Result |
|---|---|---|---|
| Criterion coverage | 7/7 | 100% of criteria | PASS |
| Assertion depth | 100% non-shallow on scrutinised items | 100% non-shallow | PASS |
| Contract completion | 10/10 | 100% of contract items | PASS |
| Discrimination sensor | 6/6 killed | 100% of mutations killed | PASS |
| Gate (gate.py build) | exit 0, 439 passed | exit 0 | PASS |

## Contract walk (C-001..C-010)

- **C-001** -- MET. `tests/unit/generation/test_language.py:146-161`
  (`test_override_naming_an_unsupported_language_is_refused_before_profile_check`) builds a
  profile whose only language is French at "professional" and asserts
  `resolve_output_language(posting, profile, override="french").allowed is False`. Read
  `src/cv_writer/generation/language.py:199-209`: the `if language not in SUPPORTED_LANGUAGES:`
  early return sits before `_resolve_pt_variant()` (line 211) and `_check_profile_supports()`
  (line 213). `gate.py quick`/`build` exit 0.
- **C-002** -- MET. `tests/unit/generation/test_language.py:164-175`
  (`test_a_posting_with_no_recognizable_language_is_refused_as_unsupported`) builds a posting
  with zero stopword hits, calls `resolve_output_language()` with no override, and asserts
  `resolution.detected == "unknown"` and `reason_code == LanguageRefusal.UNSUPPORTED_LANGUAGE`
  (not `NOT_IN_PROFILE`).
- **C-003** -- MET. `src/cv_writer/generation/language.py:125-131` -- `LanguageRefusal(str, Enum)`
  with exactly the three named members; `language.py:148` --
  `reason_code: LanguageRefusal | None = None` on `LanguageResolution`. Both construction sites
  (`language.py:200` and `:214`) supply `reason_code` on every return path. Prose `reason` is
  still populated alongside it at both sites, and `generation/pipeline.py:52` /
  `web/templates/draft.html.jinja:69` still read/render it. Three isolated refusal tests:
  `test_language.py:146-161` (`UNSUPPORTED_LANGUAGE` -- French professional profile, only the
  capability gate can fire), `test_language.py:120-133` (`NOT_IN_PROFILE` -- German override
  against an English-only profile, German is supported so only the profile-membership cause can
  fire), `test_language.py:136-143` (`BELOW_WORKING_PROFICIENCY` -- German override against a
  profile listing German at "basic", in-profile but below rank). A fourth,
  `test_language.py:178-184`, asserts an allowed resolution has `reason_code is None`.
  `test_language.py:187-190` asserts `len(LanguageRefusal) == 3` rather than pairwise
  inequality (L-007-aware). Verified by mutation #2 below that swapping BELOW_WORKING_PROFICIENCY
  for NOT_IN_PROFILE at the return site is caught.
- **C-004** -- MET. `language.py:71-88` -- `SUPPORTED_LANGUAGES["spanish"]` is a `set[str]`.
  `test_language.py:244-248` -- a Spanish posting (vocabulary excluding Portuguese-overlapping
  words) is detected as "spanish". `test_language.py:251-259` -- `variant is None` for a
  Spanish posting with no country. `test_language.py:262-264`
  (`test_spanish_stopwords_share_no_member_with_the_other_supported_languages`, parametrized
  over english/portuguese/german) asserts the intersection is empty. Verified by mutation #3
  below.
- **C-005** -- MET. `test_language.py:266-283`
  (`test_profile_proficiency_gate_allows_working_proficiency_for_every_supported_language`,
  4 ids) and `test_language.py:286-299`
  (`test_profile_proficiency_gate_refuses_basic_proficiency_for_every_supported_language`,
  4 ids) exercise the same `_check_profile_supports()` path for all four languages, asserting
  both `allowed` and `reason_code`. `_check_profile_supports()` (`language.py:243-265`) has no
  `if language == "spanish"` branch. Verified by mutation #4 below (planted a Spanish special
  case, `test_language.py:298` caught it).
- **C-006** -- MET. `src/cv_writer/generation/headings.py` exists: `SectionHeadings(BaseModel,
  frozen=True)` at `headings.py:21`, `SECTION_HEADINGS` dict at `headings.py:24-46`,
  `section_headings()` at `headings.py:57-67` normalizing with `.strip().lower()` and raising
  `ValueError` naming the offending value and the supported set on an unknown key.
  `tests/unit/generation/test_headings.py:20-28` pins English byte-for-byte;
  `test_headings.py:31-41` (parametrized pt/de/es) asserts non-empty and different from
  English; `test_headings.py:44-48` asserts case/whitespace normalization;
  `test_headings.py:51-52` asserts `set(SECTION_HEADINGS) == set(SUPPORTED_LANGUAGES)`;
  `test_headings.py:55-64` asserts `ValueError` on "french" naming both the language and every
  supported one. `render_text.py:24,33,38,43` calls `section_headings(cv.language)` and its
  `render_markdown(cv, profile)` signature is unchanged. `tests/unit/generation/test_render_text.py`:
  the shared fixture at `:24-43` deliberately avoids "Experience"/"Education"/"Skills" in
  profile-authored content, self-verified at `:46-61`; `:64-72`
  (`test_render_markdown_uses_the_resolved_language_headings`, 4 languages) asserts each
  `"## {heading}"` line is present; `:75-84`
  (`test_render_markdown_emits_no_english_heading_for_a_non_english_language`, 3 non-English
  ids) scopes the negative check to lines starting with "## " only; `:87-92` pins the English
  render exactly; `:95-107`
  (`test_render_plain_text_carries_non_english_headings_with_markdown_markers_stripped`)
  asserts both presence of the bare heading word and absence of "## " + heading. Verified by
  mutation #3 (hardcoding one heading back to English -- 8 tests failed across this file and
  C-007's) and mutation #5 (disabling the marker-strip -- only the "absent" half of the
  render_plain_text test failed, confirming the "presence-only" half alone would not have
  caught it, exactly as the contract claims).
- **C-007** -- MET. `tests/unit/generation/test_render_text_has_no_hardcoded_headings.py:81-87`
  runs the AST scan against the real `render_text.py` and asserts no offenders;
  `:90-94` guards the scan looked at a real, non-empty file; `:97-122` plant synthetic
  violations (including inside an f-string) and assert the scan catches them;
  `:125-131` asserts pure punctuation/whitespace literals are not flagged. Confirmed the scan
  passes against the current module (gate ran clean) and that mutation #3 (a reintroduced
  hardcoded "## Education") is caught by this same file's
  `test_render_text_owns_no_hardcoded_user_visible_word`.
- **C-008** -- MET. `specs/features/001-cv-writer.md` diff (5eb3582..HEAD) reworded criterion
  26's parenthetical to "a small number of clearly-labelled, consistently-named sections
  (illustrative English example) form and added a 2026-08-22 Revision-log entry naming
  "criterion 26 (spec 003)" and quoting the superseded wording verbatim.
  `tests/unit/scripts/test_spec_001_criterion_26_amendment.py:44-49` asserts the normalized
  (whitespace-collapsed) `criteria_part` no longer contains the old phrase;
  `:52-58` asserts criterion 26 still exists (`^26\. `) and still names "ATS-safe structure";
  `:61-91` asserts a post-2026-08-17 dated entry mentioning both "criterion 26" and "003".
- **C-009** -- MET. `tests/integration/generation/test_generation_pipeline.py:229-260`
  (`test_generate_cv_never_calls_the_rephraser_for_a_refused_language`) injects a `Rephraser`
  double whose `rephrase()` raises `AssertionError("the LLM was called for a refused
  language")`, calls `generate_cv()` with `language_override="french"` against a
  French-professional-only profile, and asserts (`:259-260`) the result is a
  `GenerationFailure` with a truthy `.reason`. `generation/pipeline.py:48-52` confirms the
  early return happens before the `rephraser.rephrase()` call at `:64`. Verified by mutation #1
  below.
- **C-010** -- MET. `tests/unit/web/test_language_refusal_reaches_the_user.py:54-63`
  (`test_a_refused_language_reaches_the_user_as_a_422_with_the_reason_visible`) uses
  `TestClient` over `create_app()`, POSTs `language_override=french` to
  `/drafts/{draft_id}/generate` against a French-only profile, and asserts
  `response.status_code == 422` and the refusal reason text is in `response.text`. Verified by
  mutation #1 below (this test failed alongside the pipeline test when the capability gate was
  disabled).

## Criterion evidence

| Criterion | Contract item | Evidence (file:line) | Asserted value matches the spec's stated outcome |
|---|---|---|---|
| AC-001 | C-001, C-002 | `tests/unit/generation/test_language.py:146-161`, `:164-175` | yes |
| AC-002 | C-004 | `tests/unit/generation/test_language.py:244-264` | yes |
| AC-003 | C-005 | `tests/unit/generation/test_language.py:266-299` | yes |
| AC-004 | C-006, C-007 | `tests/unit/generation/test_headings.py:20-64`, `tests/unit/generation/test_render_text.py:64-107`, `tests/unit/generation/test_render_text_has_no_hardcoded_headings.py:81-131` | yes |
| AC-005 | C-008 | `tests/unit/scripts/test_spec_001_criterion_26_amendment.py:44-91`, `specs/features/001-cv-writer.md` (diff) | yes |
| AC-006 | C-009, C-010 | `tests/integration/generation/test_generation_pipeline.py:229-260`, `tests/unit/web/test_language_refusal_reaches_the_user.py:54-63` | yes |
| AC-007 | C-003 | `tests/unit/generation/test_language.py:120-190` | yes |

No spec-precision gaps found -- every AC names a decidable outcome the tests actually assert on
(reason codes rather than prose, an enumerated set of headings, a dated log entry with named
content, an HTTP status code plus body substring).

## Assertion depth

Independently scrutinised, per the task's specific instructions:

- `tests/unit/generation/test_language.py`'s three refusal-reason tests
  (`:120-133`, `:136-143`, `:146-161`) each isolate exactly one refusal cause: the
  UNSUPPORTED_LANGUAGE fixture uses a language (French) the profile *would* otherwise permit
  at professional proficiency, so only the SUPPORTED_LANGUAGES gate can produce the refusal;
  the NOT_IN_PROFILE and BELOW_WORKING_PROFICIENCY fixtures both use German, which passes
  the SUPPORTED_LANGUAGES gate, so only the profile-membership or proficiency-rank cause can
  fire in each. Confirmed by mutation #2 (swapping the two profile-side reason codes killed
  only the proficiency-side test, not the capability-side one) and mutation #1 (disabling the
  capability gate killed the capability-side test without touching the profile-side ones) -- the
  isolation is real, not incidental.
- `tests/unit/generation/test_render_text.py`'s non-English negative assertion (`:75-84`) scopes
  to `line.startswith("## ")` before checking for "Experience"/"Education"/"Skills", so
  profile-authored content (rendered verbatim per Out-of-scope) cannot turn it red. The shared
  fixture at `:24-43` is independently checked at `:46-61` to contain none of those three words
  in the first place, closing the risk that the fixture itself silently drifted. The
  `render_plain_text()` test at `:95-107` asserts both the bare heading word is present *and*
  `"## " + heading` is absent -- mutation #5 (disabling marker-stripping) confirmed only the
  second assertion fails; the first alone would have passed against the broken code, which is
  exactly the "half that actually fails" the contract required.
- No tautologies, no bare "no exception raised" checks, no call-count-only assertions found in
  the new test files. `test_render_text_has_no_hardcoded_headings.py` and
  `test_spec_001_criterion_26_amendment.py` both include an explicit non-empty-file guard,
  which is a reasonable minimum sanity check rather than the entire assertion.

## Discrimination sensor

Isolated scratch copy: git worktree add "C:\Users\Admin\.claude\jobs\5e0376b0\tmp\scratch-003" HEAD
(left in place afterward -- not deleted, per the no-delete rule). Forced
PYTHONPATH set to the scratch worktree's src/ directory for every mutation run and verified first:

cv_writer.__file__ == C:\Users\Admin\.claude\jobs\5e0376b0\tmp\scratch-003\src\cv_writer\__init__.py

confirming imports resolved into the scratch tree, not the editable-installed original (L-006).

| # | Mutation | File | Tests expected to fail | Killed? |
|---|---|---|---|---|
| 1 | `if language not in SUPPORTED_LANGUAGES:` -> `if False:` (disable the capability gate) | `src/cv_writer/generation/language.py:199` | `test_language.py::test_override_naming_an_unsupported_language_is_refused_before_profile_check`, `::test_a_posting_with_no_recognizable_language_is_refused_as_unsupported`, `test_generation_pipeline.py::test_generate_cv_never_calls_the_rephraser_for_a_refused_language`, `test_language_refusal_reaches_the_user.py::test_a_refused_language_reaches_the_user_as_a_422_with_the_reason_visible` | yes -- 4 failed |
| 2 | Swapped LanguageRefusal.BELOW_WORKING_PROFICIENCY -> LanguageRefusal.NOT_IN_PROFILE at the proficiency-refusal return site | `src/cv_writer/generation/language.py:258` | `test_language.py::test_reason_code_is_below_working_proficiency_for_german_at_basic`, `::test_profile_proficiency_gate_refuses_basic_proficiency_for_every_supported_language` (4 ids) | yes -- 5 failed |
| 3 | Hardcoded "## Education" back into `render_markdown()` in place of `f"## {headings.education}"` | `src/cv_writer/generation/render_text.py:38` | `test_render_text.py` (multiple, all 4-language and non-English tests), `test_render_text_has_no_hardcoded_headings.py::test_render_text_owns_no_hardcoded_user_visible_word` | yes -- 8 failed |
| 4 | Planted `if language == "spanish": return True, None, None` before the general loop in `_check_profile_supports()` | `src/cv_writer/generation/language.py:246` | `test_language.py::test_profile_proficiency_gate_refuses_basic_proficiency_for_every_supported_language[spanish]` | yes -- 1 failed |
| 5 | `stripped = line.lstrip("#").strip()` -> `stripped = line` (disable Markdown-marker stripping) in `render_plain_text()` | `src/cv_writer/generation/render_text.py:53` | `test_render_text.py::test_render_plain_text_carries_non_english_headings_with_markdown_markers_stripped` | yes -- 1 failed (only the marker-absence assertion, confirming the presence-only half would not have caught it) |
| 6 | Added "team" (already in English/German sets) to `SUPPORTED_LANGUAGES["spanish"]` | `src/cv_writer/generation/language.py:88` | `test_language.py::test_spanish_stopwords_share_no_member_with_the_other_supported_languages[english]`, `[german]` | yes -- 2 failed |

6/6 mutations killed, 0 survived. Each mutation was reverted with `git checkout --` inside the
scratch worktree only; `git status --porcelain` in the real working tree was re-checked after
the run and matches the pre-session baseline exactly (the two pre-existing untracked files
only -- nothing from this session).

## Gate

`python scripts/gate.py build` run directly by the verifier (not taken on the implementer's
word): exit 0. `439 passed, 1 warning` (pytest, unrelated StarletteDeprecationWarning),
`ruff check` clean, validate_spec/validate_tasks/validate_contract all PASS for both
002 and 003.

## Ranked gaps

None. Verdict PASS.

## Lessons

A test that asserts a field is *present* after a transform (e.g. "the translated heading word
appears in the output") passes even if the transform never ran, when the untransformed input
already contained that value in a different form -- always pair the positive assertion with a
negative one on the form the untransformed input could not have produced (here: heading word
present *and* its Markdown marker absent), or the test cannot distinguish "transform worked"
from "transform never touched this".
