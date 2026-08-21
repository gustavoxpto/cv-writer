# Spec: Full-document language localization

- **ID:** 003-full-document-language-localization
- **Status:** draft
- **Size:** large
- **Author:** AI (operational-readiness follow-up) + Gustavo
- **Date:** 2026-08-19 (original sign-off); migrated into `.specs/` 2026-08-21

<!--
MIGRATION NOTE — read before re-signing.

The substance of this spec was written and signed off by Gustavo on 2026-08-19, as
`specs/features/003-full-document-language-localization.md` on branch
`feat/003-full-document-language-localization`. That file predates the harness: it uses the old
`specs/` layout and prose criteria numbered 1-6, so `validate_spec.py` cannot parse it and the
`PreToolUse` hook on `src/**` would not recognise it as signed off.

This file is that spec re-expressed in EARS with stable `AC-NNN` IDs. The intent is a faithful
translation, not a rethink — criteria 1-6 map one-to-one onto AC-001..AC-006, in order, and the
Why, Out of scope and Open questions are carried over with only the factual re-checks noted
below. Nothing was added. Anything the migration wanted to add is parked in OQ-4/OQ-5 for you to
accept or reject, rather than smuggled into a criterion.

Because the IDs are new and the wording is tighter, Status returns to `draft` and both sign-off
boxes are unticked. The 2026-08-19 sign-off covered different text. This should be a short
re-read, not a fresh decision: the substantive calls, including OQ-1, are already made.

The original file is NOT deleted or moved — it stays on its branch as the historical record,
consistent with AD-001's treatment of spec 001.

Re-verified against the code on 2026-08-21, after spec 002 merged its changes into ingestion:
  - SUPPORTED_LANGUAGES is still {english, german, portuguese} — Spanish is still absent.
  - render_text.py still hardcodes "## Experience" / "## Education" / "## Skills" (lines 26, 31, 36).
  - resolve_output_language() still validates `override` only against the profile's languages.
So every failure this spec describes is still live.
-->

## Why

The first real end-to-end run (2026-08-19, against a Spanish posting) produced a CV with English
section headings — "Experience", "Education", "Skills" — over Spanish bullet content. A
half-translated document nobody would send. Two root causes, both traced in code:

- `generation/render_text.py`'s `render_markdown()` hardcodes those three English words. Only
  `cv.accepted_bullets` passes through the LLM rephraser with a target language
  (`rephraser.py::_build_prompt`, "in {request.target_language}{variant_note}"); headings are
  never translated at all.
- `generation/language.py`'s `resolve_output_language()` accepts any `override` string and checks
  it only against the profile's `languages`, never against `SUPPORTED_LANGUAGES` — the set
  `detect_posting_language()` actually knows. An override naming a language the tool has no other
  support for sails through as `allowed=True` so long as the profile lists it at working
  proficiency, even though nothing downstream except the rephraser prompt knows how to render
  that language's structure.

Criterion 20 of spec 001 is silent on whether "the CV" means the bullets or the whole document;
the original implementation read it as bullets-only. Criterion 26 additionally names "standard
section headings (Experience, Education, Skills)" as part of the ATS-safety checklist — read
literally, that mandates the English words even when the rest of the document is in another
language, which is the bug's other root cause and needs amending rather than working around.

The posting that surfaced this was Spanish, and Spanish is not a supported language at all today
(`SUPPORTED_LANGUAGES` holds only english/portuguese/german). So this spec adds it as a fourth,
rather than closing the override bypass and leaving Spanish postings refused — which would take a
tool that produced a bad Spanish CV and make it produce none.

**Relationship to spec 002.** Spec 002 taught *ingestion* to read Spanish postings; that shipped
and a real posting now extracts eleven requirements instead of one. This spec is the other half:
the tool can now understand a Spanish posting it still cannot write a CV for.

## Acceptance criteria

- **AC-001** — IF `resolve_output_language()` is given an `override` naming a language absent from
  `SUPPORTED_LANGUAGES`, THEN the system SHALL refuse it (`allowed=False`) with a reason distinct
  from the existing "not in profile" and "below working proficiency" reasons, and SHALL perform
  that check before any profile-proficiency check.
- **AC-002** — The system SHALL include Spanish in `SUPPORTED_LANGUAGES` with its own curated
  stopword set, and `detect_posting_language()` SHALL identify a Spanish posting the same flat way
  it already identifies English and German, with no variant mechanism.
- **AC-003** — WHERE Spanish is the resolved output language, the system SHALL apply the same
  profile-proficiency gate it applies to the other three languages (`_check_profile_supports()`
  against `MINIMUM_WORKING_RANK`), with no special-casing.
- **AC-004** — WHEN rendering a CV, the system SHALL emit its own structural strings — at minimum
  the section headings for experience, education and skills in `render_markdown()` — in the
  resolved output language, for all four supported languages.
- **AC-005** — The repository SHALL carry an explicit, dated amendment to spec 001's criterion 26,
  rewording "standard section headings (Experience, Education, Skills)" as an illustrative English
  example of the ATS-safe pattern — a small number of clearly-labelled, consistently-named
  sections — rather than a mandate to emit those English words regardless of output language.
- **AC-006** — IF generation is requested for a language absent from `SUPPORTED_LANGUAGES`, THEN
  the system SHALL fail before any LLM call is made, and the reason SHALL reach the user through
  the existing `generate_draft_cv()` re-render path.

### Criterion → test placement

| Criteria | Lives in |
|---|---|
| AC-001, AC-002, AC-003 | `tests/unit/generation/` |
| AC-004 | `tests/unit/generation/` |
| AC-005 | `tests/unit/scripts/` — a documentation sensor; see OQ-4 |
| AC-006 | `tests/unit/generation/`, `tests/integration/generation/` |

## Out of scope

- **The numeric-formatting false rejection in `generation/validator.py`** (locale spacing, "100 %"
  against a stored "100%"), carried over from spec 002's own out-of-scope list. It sits on the
  anti-fabrication path and wants its own spec.
- **Translating profile-authored content** — `education[].degree`, `.institution`,
  `skills[].name`. Resolved at the 2026-08-19 sign-off: these stay verbatim. Translating a
  person's real credentials is fabrication-adjacent (criterion 19), and institution names
  generally should not be translated on a CV at all.
- **A PT-PT/PT-BR-style variant mechanism for Spanish.** One flat language.
- **Localizing anything outside `render_text.py`'s own control strings.** This is about the
  generated CV artifact, not the web UI's English chrome.
- **Changing `render_html.py`'s `language` semantics** beyond staying consistent — it already
  receives `cv.language` at both call sites.
- **The preferred-vs-required language bug found by spec 002** — a language named under a
  preferred heading ("Se valorará: alemán") is reported as required, because only skills are
  zoned. Real defect, adjacent to this work, and not covered by any criterion here.

## Open questions

- [x] **OQ-1** (non-blocking) — **Resolved at the 2026-08-19 sign-off: profile-authored content
      stays verbatim.** See Out of scope.
- [ ] **OQ-2** (non-blocking) — The proposed heading translations are a draft, not a linguistic
      authority: Portuguese "Experiência Profissional / Formação / Competências", German
      "Berufserfahrung / Ausbildung / Kenntnisse", Spanish "Experiencia / Educación /
      Habilidades". Worth a native-speaker read before or soon after merge — the same caveat
      spec 001 already carries for PT-PT.
- [ ] **OQ-3** (non-blocking) — Should `render_html.py`'s `language` value (currently the full
      lowercase word, used for the HTML `lang` attribute) become a BCP-47 code — "en", "pt", "es",
      "de"? Semantically correct, required by no criterion here.
- [ ] **OQ-4** (blocking) — **How is AC-005 sensed?** It is the only criterion whose subject is a
      document rather than behaviour. Options: a unit test asserting spec 001's file contains the
      amendment text; a manual review checkbox; or dropping it as a criterion and handling the
      amendment as an ordinary docs commit. This must be settled before sign-off, because a
      criterion no sensor can decide is exactly what `validate_spec.py` and the contract phase
      exist to prevent.
- [ ] **OQ-5** (non-blocking, opened at migration) — AC-004 says "at minimum the section
      headings". Is anything else in `render_text.py` a user-visible structural string today, or
      is that the complete list? If it is complete, the "at minimum" hedge should go, since a
      criterion with an open edge is hard to call done.

## Sign-off

- [ ] Human has read this and understands the *why*, not just the *what*.
- [ ] Acceptance criteria are specific enough to write failing tests from.

*(Implementation does not start until both boxes are checked and Status is `signed-off`. The
`PreToolUse` hook on `src/**` enforces this. The 2026-08-19 sign-off applied to the pre-migration
text and does not carry over — see the migration note at the top. OQ-4 is blocking and must be
resolved first.)*
