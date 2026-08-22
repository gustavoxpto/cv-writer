# PR body — Spec 003: full-document language localization (AC-001..AC-007)

- **Spec:** `.specs/features/003-full-document-language-localization/spec.md` (signed off, Gustavo, 2026-08-21)
- **Design:** `.specs/features/003-full-document-language-localization/design.md`, `specs/adr/0006-output-language-localization-shape.md`
- **Contract:** `.specs/features/003-full-document-language-localization/contract.md` (C-001..C-010, verifier-signed)
- **Validation:** `.specs/features/003-full-document-language-localization/validation.md` — **PASS**
- **Pairing note:** `pairing/sessions/2026-08-22-spec-003-full-document-language-localization.md`

## What & why

The first real end-to-end run, on 2026-08-19 against a Spanish job posting, produced a CV with
English section headings — "Experience", "Education", "Skills" — sitting over Spanish bullet
content. A half-translated document nobody would send.

Two root causes, both in `src/cv_writer/generation/`:

- **`render_text.py` hardcoded the three English headings.** Only `cv.accepted_bullets` ever
  passed through the LLM rephraser with a target language. The document's own structural strings
  were never translated at all.
- **`language.py::resolve_output_language()` validated an `override` only against the profile's
  `languages`, never against `SUPPORTED_LANGUAGES`** — the set `detect_posting_language()`
  actually knows. An override naming a language the tool has no other support for sailed through
  as `allowed=True` so long as the profile listed it at working proficiency, even though nothing
  downstream except the rephraser prompt knew how to render that language's structure.

The posting that surfaced this was Spanish, and Spanish was not a supported language at all. So
this slice adds it as a fourth, rather than closing the override bypass and leaving Spanish
postings refused — which would have taken a tool that produced a bad Spanish CV and made it
produce none.

This is the other half of spec 002. That slice taught *ingestion* to read Spanish postings; a real
posting now extracts eleven requirements instead of one. The tool could understand a Spanish
posting it still could not write a CV for.

## What's in it

**The capability gate (AC-001, AC-007).** `resolve_output_language()` now refuses any resolved
language absent from `SUPPORTED_LANGUAGES` — whether it came from the caller's `override` or from
`detect_posting_language()`, including its `"unknown"` sentinel — *before* PT-variant resolution
and before the profile is consulted at all. Capability before permission. A refused
`LanguageResolution` now carries a machine-readable `reason_code`: a `LanguageRefusal(str, Enum)`
with exactly three members, `UNSUPPORTED_LANGUAGE`, `NOT_IN_PROFILE` and
`BELOW_WORKING_PROFICIENCY`, so "a reason distinct from the existing ones" is decidable without
freezing prose in tests. The human-readable `reason` string is unchanged and still populated —
`generation/pipeline.py` reads it and `draft.html.jinja` renders it.

**Spanish as a fourth language (AC-002, AC-003).** A curated Spanish stopword set, disjoint from
English's, Portuguese's and German's, detected the same flat way as the others with no
PT-PT/PT-BR-style variant mechanism. The profile-proficiency gate applies to it identically, with
no special-casing — proven by one parametrized test over all four languages rather than a
Spanish-specific one.

**Localized headings (AC-004).** A new `generation/headings.py` holds a frozen `SectionHeadings`
model and a language-keyed `SECTION_HEADINGS` map. `render_markdown()` now calls
`section_headings(cv.language)` instead of emitting literals; its `(cv, profile)` signature is
unchanged, so `write_output.py` and `web/routes.py` are untouched. `render_plain_text()` derives
from `render_markdown()` and inherits the localization for free. A new AST sensor
(`test_render_text_has_no_hardcoded_headings.py`) parses `render_text.py` and fails if any string
literal contains two or more consecutive ASCII letters — so the module can never quietly reacquire
a user-visible word of its own. The sensor includes a planted-violation case proving it catches
what it claims to.

**The spec 001 amendment (AC-005).** Criterion 26 named "standard section headings (Experience,
Education, Skills)" in its ATS-safety checklist. Read literally, that mandated the English words
regardless of output language — this slice's own bug, written into a signed criterion. The bullet
is reworded so the parenthetical is an illustrative English example of the ATS-safe pattern (a
small number of clearly-labelled, consistently-named sections), with a dated Revision-log entry
quoting the superseded wording verbatim. The criterion is amended, never deleted. A documentation
sensor fails if either the amended text or its log entry goes missing.

**The refusal path (AC-006).** Two tests pin existing behaviour as sensors: a `Rephraser` double
whose `rephrase()` raises proves no LLM call is made for a refused language, and a `TestClient`
test proves the refusal reaches the user as an HTTP 422 with the reason visible in the body.

## Acceptance criteria covered

| Criterion | Covered by | Evidence |
|---|---|---|
| **AC-001** — unsupported resolved language refused, before profile and PT-variant checks | T-003 | `src/cv_writer/generation/language.py:199-220` |
| **AC-002** — Spanish supported, detected flat, no variant | T-004 | `src/cv_writer/generation/language.py:71-88` |
| **AC-003** — same proficiency gate for Spanish, no special-casing | T-005 | `tests/unit/generation/test_language.py:267-299` |
| **AC-004** — structural strings emitted in the resolved language | T-006, T-007, T-008 | `src/cv_writer/generation/headings.py`, `render_text.py:22-47` |
| **AC-005** — dated amendment to spec 001 criterion 26 | T-009 | `specs/features/001-cv-writer.md`, `tests/unit/scripts/test_spec_001_criterion_26_amendment.py` |
| **AC-006** — refusal before any LLM call, reaching the user | T-010, T-011 | `tests/integration/generation/test_generation_pipeline.py:229-260`, `tests/unit/web/test_language_refusal_reaches_the_user.py:54-63` |
| **AC-007** — machine-readable refusal reason code | T-002 | `src/cv_writer/generation/language.py:125-148` |

Eleven tasks, eleven atomic commits, one per task, each gated before it landed.

## Validation

Independent verifier, fresh context, `validation.md`:

| Check | Score | Minimum | Verdict |
|---|---|---|---|
| Criterion coverage | 7/7 | 100% | PASS |
| Contract completion | 10/10 | 100% | PASS |
| Assertion depth | 100% non-shallow | 100% | PASS |
| Discrimination sensor | 6/6 mutations killed | 100% | PASS |
| `gate.py build` | exit 0, 439 passed | exit 0 | PASS |

Test count went from 296 to 439. No spec-precision gaps.

Mutation testing ran in an isolated tree outside the repository with `PYTHONPATH` forced and
`cv_writer.__file__` confirmed to resolve there *before* any result was believed — `.specs/LESSONS.md`
L-006 exists because a previous verifier reported 35/35 while testing unmutated code. Two of the
six mutations were then independently reproduced by the orchestrating session in a separate tree:
disabling the `SUPPORTED_LANGUAGES` gate is killed by the AC-001 and AC-002 tests, and pinning
`render_markdown()` to English headings is killed by seven tests in `test_render_text.py`.

## Checklist

- [x] Spec is signed off — `.specs/features/003-full-document-language-localization/spec.md`
- [x] Tests written before implementation (TDD) — see the note on T-001/T-005 below
- [ ] CI passing — pending on this PR
- [x] No secrets committed (see `docs/security.md`)
- [x] Pairing notes added — `pairing/sessions/2026-08-22-spec-003-full-document-language-localization.md`

### Reviewer: worth a look

The places where a different decision was defensible. This is the part worth arguing with.

1. **The contract was rejected once before any code was written, and that is the real story of
   this PR.** Two of its ten items could not have been discharged as written.
   - **C-003** required a machine-readable `reason_code`, then ended its check with "confirm no
     existing call site that constructs `LanguageResolution(...)` was edited to supply
     `reason_code`". There is exactly one such site — the return of `resolve_output_language()` —
     and it is precisely the one that must be edited, or the field is `None` on every refusal and
     AC-007 cannot be discharged. The check forbade the change the item required.
   - **C-006** asked only that the English headings be "non-empty", which pins nothing. Nothing
     else in the suite pinned them either: the `## Experience` strings elsewhere under `tests/`
     are hand-written Markdown *inputs* to `render_html`/`page_fit`, never assertions on
     `render_markdown()`'s output. English output could have drifted with every gate green. Its
     negative assertion also ran over the whole rendered document, which carries profile-authored
     content verbatim — an English bullet or skill name would have failed it for reasons entirely
     unrelated to headings.

   Both were rewritten and the full list re-signed. Worth asking whether the contract phase caught
   these because it is well designed, or because this feature happened to have an unusually
   checkable shape.

2. **A process gap worth an actual decision.** `tasks.md` was written *before* the contract was
   signed. When the contract was fixed, three tasks still described the rejected shape and had to
   be re-synced (`5eb3582`) — including a sequencing trap where T-002's fixture, left on an
   unsupported language, would have passed at T-002 and flipped to a different reason code once
   T-003 landed the capability gate, turning T-002's own tests red inside T-003's commit. Should
   Tasks run *after* Contract, or should a contract change force a tasks re-check? Nothing in the
   harness enforces either today.

3. **T-001 and T-005 have no red phase.** Both are behaviour-neutral by design — T-001 moves a
   test fixture from French to German ahead of the gate that would have broken it for an unrelated
   reason, T-005 parametrizes a path T-004 already opened. Defensible, and each task's "Done when"
   says so explicitly, but it is a departure from strict TDD and the reviewer should agree with it
   rather than let it pass unremarked.

4. **T-002's `len(LanguageRefusal) == 3` and "an allowed resolution has no `reason_code`"
   assertions landed in T-003's commit**, because the three-way discrimination only becomes
   meaningful once `UNSUPPORTED_LANGUAGE` is reachable. Reasonable, but it blurs
   one-commit-per-task.

5. **The heading translations are AI-drafted (OQ-2, open, non-blocking).** Portuguese
   "Experiência Profissional / Formação / Competências", German "Berufserfahrung / Ausbildung /
   Kenntnisse", Spanish "Experiencia / Educación / Habilidades". These ship as a best effort and
   want a native-speaker read — the same caveat spec 001 already carries for PT-PT.

6. **`section_headings()` raises `ValueError` rather than falling back to English** (design
   decision 4, L-004: prefer a loud failure to a quiet wrong result). The silent fallback *is* the
   bug this slice exists to fix, so the loud version is deliberate — but it means an unsupported
   `cv.language` reaching the renderer is now an exception rather than a degraded document.

7. **`headings.py` deliberately imports nothing from `cv_writer`** (design boundary B3), so
   `set(SECTION_HEADINGS) == set(SUPPORTED_LANGUAGES)` is asserted in the test rather than derived
   in the module. Deriving it would have made drift impossible instead of merely detectable; the
   boundary was judged worth more. Reasonable people could take the other side.

8. **Still open, explicitly out of scope.** OQ-3: `render_html.py`'s `lang` attribute is still the
   full lowercase word (`lang="spanish"`, not BCP-47 `"es"`) — invalid before this slice and
   invalid after, unchanged rather than newly broken. And the Spanish/Portuguese near-tie in
   `detect_posting_language()` is still resolved by dict insertion order (design concern 2); no
   criterion here asked for confidence-aware scoring, so none was built.
