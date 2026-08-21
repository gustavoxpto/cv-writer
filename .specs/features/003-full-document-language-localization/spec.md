# Spec: Full-document language localization

- **ID:** 003-full-document-language-localization
- **Status:** signed-off
- **Size:** large
- **Author:** AI (operational-readiness follow-up) + Gustavo
- **Date:** 2026-08-19 (original sign-off); migrated into `.specs/` and re-signed 2026-08-21

<!--
MIGRATION NOTE — how this spec got here.

The substance of this spec was written and signed off by Gustavo on 2026-08-19, as
`specs/features/003-full-document-language-localization.md` on branch
`feat/003-full-document-language-localization`. That file predates the harness: it uses the old
`specs/` layout and prose criteria numbered 1-6, so `validate_spec.py` cannot parse it and the
`PreToolUse` hook on `src/**` would not recognise it as signed off.

This file is that spec re-expressed in EARS with stable `AC-NNN` IDs. The intent is a faithful
translation, not a rethink — criteria 1-6 map one-to-one onto AC-001..AC-006, in order, and the
Why, Out of scope and Open questions are carried over with only the factual re-checks noted
below. Nothing was added at migration time. The two things the migration wanted to change were
parked as OQ-4 and OQ-5 rather than smuggled into a criterion, and both were then decided by
Gustavo at re-sign — see those entries for what changed and why.

Because the IDs were new and the wording tighter, Status went back to `draft` with both boxes
unticked — the 2026-08-19 sign-off covered different text. Gustavo re-signed the migrated form on
2026-08-21, resolving OQ-4 and OQ-5 in the process. The substantive calls from 2026-08-19,
including OQ-1, carried over unchanged.

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

- **AC-001** — IF `resolve_output_language()` resolves to a language absent from
  `SUPPORTED_LANGUAGES` — whether that language came from the caller's `override` or from
  `detect_posting_language()`, including its `"unknown"` sentinel — THEN the system SHALL refuse
  it (`allowed=False`) with a reason distinct from the existing "not in profile" and "below
  working proficiency" reasons, and SHALL perform that check before any profile-proficiency check
  and before any Portuguese-variant resolution. *(Amended 2026-08-21 — see Revision log R-1.)*
- **AC-002** — The system SHALL include Spanish in `SUPPORTED_LANGUAGES` with its own curated
  stopword set, and `detect_posting_language()` SHALL identify a Spanish posting the same flat way
  it already identifies English and German, with no variant mechanism.
- **AC-003** — WHERE Spanish is the resolved output language, the system SHALL apply the same
  profile-proficiency gate it applies to the other three languages (`_check_profile_supports()`
  against `MINIMUM_WORKING_RANK`), with no special-casing.
- **AC-004** — WHEN rendering a CV, the system SHALL emit each of its own structural strings —
  the experience, education and skills section headings in `render_markdown()`, which OQ-5
  establishes are the complete set — in the resolved output language, for all four supported
  languages. `render_plain_text()` derives from `render_markdown()` and inherits this.
- **AC-005** — The repository SHALL carry an explicit, dated amendment to spec 001's criterion 26,
  rewording "standard section headings (Experience, Education, Skills)" as an illustrative English
  example of the ATS-safe pattern — a small number of clearly-labelled, consistently-named
  sections — rather than a mandate to emit those English words regardless of output language. The
  amendment SHALL be recorded as a dated entry in that spec's own "Revision log", following the
  2026-08-17 entry's form, and a test SHALL fail if either the amended criterion text or its
  revision-log entry is absent (OQ-4, resolved at re-sign).
- **AC-006** — IF generation is requested for a language absent from `SUPPORTED_LANGUAGES`, THEN
  the system SHALL fail before any LLM call is made, and the reason SHALL reach the user through
  the existing `generate_draft_cv()` re-render path.
- **AC-007** — WHEN `resolve_output_language()` refuses, the resolution it returns SHALL carry a
  machine-readable reason code identifying which of the three refusal causes applied —
  unsupported language, language absent from the profile, or proficiency below working level —
  so that AC-001's "distinct reason" is decidable without asserting on prose.
  *(Added 2026-08-21 — see Revision log R-2.)*

### Criterion → test placement

| Criteria | Lives in |
|---|---|
| AC-001, AC-002, AC-003, AC-007 | `tests/unit/generation/` |
| AC-004 | `tests/unit/generation/` |
| AC-005 | `tests/unit/scripts/` — a documentation sensor over `specs/features/001-cv-writer.md` |
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
- [x] **OQ-4** (blocking) — **Resolved at re-sign, 2026-08-21: a documentation sensor.** AC-005
      is discharged by a unit test in `tests/unit/scripts/` asserting two things about
      `specs/features/001-cv-writer.md` — that criterion 26 no longer reads as a mandate for the
      English words, and that a dated entry recording the amendment exists in its Revision log.
      Rejected: a manual review checkbox (a criterion no sensor decides is what the contract phase
      exists to catch) and dropping AC-005 to an ordinary docs commit (the amendment is load-bearing
      — without it AC-004 contradicts a signed criterion, and that contradiction should be visible
      to a sensor rather than resolved in someone's head). Note the limit honestly: the test proves
      the amendment is *present*, not that it is *well worded*. That part is the human review.
- [x] **OQ-5** (non-blocking) — **Resolved by inspection at re-sign, 2026-08-21: the three
      headings are the complete set,** so AC-004 was tightened from "at minimum" to an enumeration.
      `render_text.py` was read in full. Its only literal user-visible strings are `"## Experience"`,
      `"## Education"` and `"## Skills"`. Everything else the module emits is profile-authored data
      (name, email, phone, location, link labels, degree, institution, skill names) or punctuation
      used as a separator (`" | "`, `", "`, `"- "`, `"#"`). `render_plain_text()` adds no strings of
      its own — it strips Markdown from `render_markdown()`'s output. If a later slice adds a
      fourth section, it adds a criterion with it.

## Revision log

Spec 001's convention: an amendment to a signed criterion is recorded, never made silently. AC
IDs are stable, so a changed criterion says here what changed and why.

- **R-1 (2026-08-21) — AC-001 widened from the override path to the resolved language.** The
  design phase traced `resolve_output_language()` and found that gating only `override` leaves
  `detect_posting_language()` free to resolve to a language absent from `SUPPORTED_LANGUAGES`,
  including its `"unknown"` sentinel — the same hole AC-001 exists to close, reached by the other
  door. The design implemented the wider gate; rather than let a criterion quietly do more than
  it says (the failure the verifier struck C-007 for on spec 002), the criterion was widened to
  match and the spec re-signed. Also names the ordering against `_resolve_pt_variant()`, which
  the original wording left open.

- **R-2 (2026-08-21) — AC-007 added for the machine-readable refusal reason.** The design proposed
  a `reason_code` enum on `LanguageResolution` so AC-001's "distinct reason" could be asserted
  without freezing prose in tests. Nothing in the spec named it. Rejected the alternative of
  treating it as an unnamed implementation detail of AC-001: it changes a public model shape, and
  a contract item should be able to discharge it by name. Rejected prose-only reasons: asserting
  that three sentences differ means pinning the sentences, after which ordinary rewording turns a
  test red and the tempting fix is to loosen it.

## Sign-off

- [x] Human has read this and understands the *why*, not just the *what*. — Gustavo, 2026-08-21,
      re-signing the migrated text after the 2026-08-19 sign-off of the pre-migration form, and
      again after the design phase produced amendments R-1 and R-2.
- [x] Acceptance criteria are specific enough to write failing tests from. — Gustavo, 2026-08-21.
      Resolutions made across the two re-signs: OQ-4 (AC-005 gets a documentation sensor), OQ-5
      (AC-004 tightened to an enumeration), R-1 (AC-001 widened to the resolved language) and R-2
      (AC-007 added for the refusal reason code).

*(Signed off 2026-08-21, re-signed the same day after Design. Design is complete —
`design.md` and `specs/adr/0006-output-language-localization-shape.md`. Next phase is Tasks — this spec is sized `large`, so unlike spec 002 it
gets a `design.md` and an ADR before tasks: it spans `language.py` and `render_text.py`, adds a
fourth supported language, and amends another signed spec. OQ-2 and OQ-3 remain open and
non-blocking.)*
