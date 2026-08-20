# Spec: Requirement/skill dictionary expansion

- **ID:** 002-requirement-dictionary-expansion
- **Status:** draft
- **Size:** medium
- **Author:** AI (operational-readiness session) + Gustavo
- **Date:** 2026-08-19 (retrofitted into `.specs/` 2026-08-20)

<!--
Retrofitted from specs/features/002-requirement-dictionary-expansion.md as the first feature to
run through the six-phase loop. The Why below is unchanged in substance; the acceptance criteria
were re-expressed in EARS notation with stable AC-NNN IDs so the sensors can check them.
-->

## Why

The first real end-to-end run (`docs/handoff-operational-readiness.md`'s checklist, executed
2026-08-19 against a live Lidl Spain posting) found that
`src/cv_writer/ingestion/requirements.py`'s `SKILL_TERMS` dictionary is entirely
software-engineering vocabulary (`python`, `docker`, `kubernetes`, `react`) — a leftover from
spec 001's example persona, "Ana Example, Backend Engineer". It has zero coverage for Gustavo's
actual profession: language instruction, instructional design, stakeholder management, business
consulting. `_PREFERRED_SECTION_MARKERS` and `LANGUAGE_TERMS` are English-only, so a
Spanish-language posting's own requirement wording ("se valorará", "inglés", "alemán") is not
recognized either.

Together this meant a real posting with clearly stated, matchable requirements produced a match
report containing **one** requirement (seniority) and then
`Generation failed: no evidence available to generate a CV from` — not because the profile
lacked evidence, but because extraction never surfaced anything to match it against. A quiet
empty result rather than a loud failure (`.specs/LESSONS.md` L-004).

This is spec 001's own open question 4 — *"Skill extraction quality… when it misses obvious
requirements, does it graduate to an LLM extraction step?"* — arriving as a reproduced failure
rather than a hypothetical.

**What happened in the moment.** Rather than block the real run on a redesign, Gustavo authorized
a small, scoped, reviewed addition directly to `SKILL_TERMS` / `LANGUAGE_TERMS` /
`_PREFERRED_SECTION_MARKERS` (see the "Added 2026-08-19" comments in `requirements.py`), covering
exactly the terms in that one posting. All 277 existing tests and `ruff check` passed unchanged;
**no test was added for the new terms.** That stopgap unblocked the run. It is not a durable
answer, and it is untested behaviour sitting in `src/`. This spec turns it into one.

**Where that stopgap now lives.** On 2026-08-20 Gustavo chose to *commit* it rather than carry it
as an uncommitted working-tree change or revert it (`fix(002)` on `feat/harness-engineering`).
The reasoning, on the record because it is an exception to this repo's own rules: the terms are a
fix that real applications need now, an uncommitted tree is a worse place to keep behaviour than
a labelled commit, and `git revert` stays available if this spec's design supersedes it. The cost
is knowingly accepted — untested behaviour reaching `main`, which is exactly what hard rule #4
exists to prevent, on the harness's first week. It is bounded by being written down here, by
Appendix A pinning the exact surface, and by AC-002/AC-005 owing tests for it.

## Acceptance criteria

- **AC-001** — The system SHALL load skill and requirement terms from a versioned YAML data file,
  in the same shape as `src/cv_writer/generation/data/pt_pt_terms.yaml`, rather than from a
  hardcoded Python dictionary.
- **AC-002** — The term file SHALL contain every canonical key and every phrase listed in
  Appendix A (the terms added ad hoc on 2026-08-19), with no loss of coverage relative to the
  hardcoded dictionary it replaces.
- **AC-003** — WHEN a posting contains a Spanish or Portuguese requirement-section marker
  ("se valorará" — see Appendix A.3 — plus "requisitos", "diferenciais"), the system SHALL
  recognize that section as preferred or required, matching the behaviour it already has for the
  English markers.
- **AC-004** — WHERE a language has a native-language name (the three in Appendix A.2 —
  "inglés", "español", "alemán" — plus "português", "français"), the system SHALL treat that name
  as a synonym for the canonical language key.
- **AC-005** — The system SHALL extract more than one requirement from the redacted Lidl (Spain)
  posting fixture captured on 2026-08-19, and that fixture SHALL be committed under `tests/`.
- **AC-006** — WHILE scoring a match, the system SHALL make no LLM call, preserving criterion 14
  of spec 001 — this change widens only what the deterministic extractor recognizes, never how
  matching scores.

### Criterion → test placement

| Criteria | Lives in |
|---|---|
| AC-001, AC-002, AC-004 | `tests/unit/ingestion/` |
| AC-003, AC-006 | `tests/unit/ingestion/`, `tests/unit/matching/` |
| AC-005 | `tests/integration/ingestion/` |

## Out of scope

- **Graduating extraction to an LLM-assisted step** (spec 001's open question 4 proper). A bigger
  decision that trades determinism for coverage. This spec keeps the dictionary approach and just
  makes it honest about non-English, non-engineering postings.
- **Any change to `matching/matcher.py`'s scoring formula or `generation/validator.py`'s
  anti-fabrication checks.**
- **A locale-formatting bug found in the same session.** `generation/validator.py`'s numeric-claim
  check (`_check_numeric_claims` / `_token_matches_haystack`) does exact substring matching
  between a generated numeric token and the source bullet's `metric` field, so Spanish and German
  typographic conventions (a space before the percent sign, "100 %" against a stored "100%")
  produce false rejections. Worked around by adding space-variant text to the affected bullets'
  `metric.baseline` in `data/profile.yaml`, not by touching the validator — the anti-fabrication
  path is safety-critical and deserves its own spec, not a same-session patch. Worth a dedicated
  follow-up: normalize whitespace before comparing numeric tokens, or accept a documented list of
  locale-specific unit-spacing variants.

## Open questions

- [ ] **OQ-1** (non-blocking) — Hand-maintain the term list centrally (fine for a single-user
      tool, per spec 001 criterion 35), or derive canonical skill keys automatically from
      `data/profile.yaml`'s own skill names at ingestion time? The latter means less duplication
      but couples ingestion to the profile schema in a new way.
- [ ] **OQ-2** (non-blocking) — Should a fresh `data/profile.yaml` (someone forking this harness)
      ship with a starter term list for some common non-engineering professions, or is "grow it
      from your own first real posting" the intended workflow, consistent with how the PT-PT term
      list is meant to grow?

## Appendix A — the stopgap terms (committed 2026-08-20, untested)

The authoritative list of what the 2026-08-19 ad hoc widening actually added, so that the spec —
not a code comment — is the durable record. The implementation of AC-001 must carry all of it
into the YAML term file. Phrases are reproduced verbatim, including accents; canonical keys were
chosen to textually match the profile's own skill names (see
`matching/matcher.py::_skill_name_matches`).

### A.1 — `SKILL_TERMS` (8 new canonical keys)

| Canonical key | Phrases |
|---|---|
| `stakeholder management` | "stakeholders", "stakeholder management" |
| `project planning` | "gestión de proyectos", "planificación de proyectos", "planificación anual de proyectos", "project management" |
| `instructional design` | "capacitarás", "capacitación", "formación básica y avanzada", "formación teórico-práctica" |
| `cross-functional collaboration` | "transversal", "trabajo transversal", "afectación transversal" |
| `problem solving` | "resolución de problemas" |
| `strategic consulting` | "consultoría estratégica" |
| `microsoft office` | "paquete office", "microsoft office" |
| `google workspace` | "entorno google", "google workspace" |

### A.2 — `LANGUAGE_TERMS` (3 synonyms added to existing keys)

| Canonical key | Phrase added |
|---|---|
| `english` | "inglés" |
| `spanish` | "español" |
| `german` | "alemán" |

### A.3 — `_PREFERRED_SECTION_MARKERS` (1 added)

| Marker | Means |
|---|---|
| "se valorará" | Spanish for "will be valued" — the section that follows is *preferred*, not required |

### A.4 — What is deliberately *not* here

These terms cover exactly one posting. They are a sample, not a vocabulary: no Portuguese skill
phrases, no required-section markers in either language ("requisitos", "diferenciais" — owed by
AC-003), and no native names for Portuguese or French (owed by AC-004). Treat Appendix A as the
floor the YAML file must clear, never as the target.

## Sign-off

- [ ] Human has read this and understands the *why*, not just the *what*.
- [ ] Acceptance criteria are specific enough to write failing tests from.

*(Implementation does not start until both boxes are checked and Status is `signed-off`. The
`PreToolUse` hook on `src/**` enforces this. The ad hoc widening now committed in
`requirements.py` is a stopgap authorized for one real run, not a substitute for sign-off — and
it is untested, which is what AC-002 and AC-005 exist to fix.)*
