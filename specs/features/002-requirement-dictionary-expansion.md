> **Superseded in place.** The live version of this spec is
> `.specs/features/002-requirement-dictionary-expansion/spec.md`, retrofitted 2026-08-20 into
> the six-phase loop with EARS criteria and stable `AC-NNN` IDs. Same Why, same scope; the
> criteria were re-expressed so the sensors can check them. This file is kept as the original
> record (see `AD-001` in `.specs/STATE.md`).

# Spec: Requirement/skill dictionary expansion

- **Status:** draft
- **Author:** AI (operational-readiness session) + Gustavo, 2026-08-19
- **Date:** 2026-08-19

## Why

The first real end-to-end run (`docs/handoff-operational-readiness.md`'s checklist, executed
2026-08-19 against a live Lidl Spain posting — see `pairing/sessions/` for the session log)
found that `src/cv_writer/ingestion/requirements.py`'s `SKILL_TERMS` dictionary is entirely
software-engineering vocabulary (`python`, `docker`, `kubernetes`, `react`, ...) — a leftover
from spec 001's example persona ("Ana Example, Backend Engineer"). It has zero coverage for
Gustavo's actual profession (language instruction, instructional design, stakeholder
management, business consulting), and `_PREFERRED_SECTION_MARKERS`/`LANGUAGE_TERMS` are
English-only, so a Spanish-language posting's own requirement wording ("se valorará", "inglés",
"alemán") isn't recognized either. Together this meant a real posting with clearly-stated,
matchable requirements produced a match report with only one requirement found (seniority) and
a `Generation failed: no evidence available to generate a CV from` refusal — not because the
profile lacked evidence, but because extraction never surfaced anything to match it against.

This is spec 001's own open question 4 ("Skill extraction quality... when it misses obvious
requirements, does it graduate to an LLM extraction step?") arriving as a concrete, reproduced
failure rather than a hypothetical.

**What happened in the moment:** rather than block the real run on a full redesign, Gustavo
authorized a small, scoped, reviewed addition directly to `SKILL_TERMS`/`LANGUAGE_TERMS`/
`_PREFERRED_SECTION_MARKERS` in `src/cv_writer/ingestion/requirements.py` (see the "Added
2026-08-19" comments there), covering exactly the terms in that one Lidl posting. All 277
existing tests and `ruff check` passed unchanged; no test was added for the new terms. That
ad hoc fix unblocked today's run but isn't a durable answer — this spec is the follow-up to
turn it into one.

## What (acceptance criteria)

1. The skill/requirement dictionary becomes a versioned, data-driven file (YAML, same shape as
   `src/cv_writer/generation/data/pt_pt_terms.yaml`), not a hardcoded Python dict — extendable
   without touching code, matching the precedent already set for the PT-PT checker.
2. Coverage is no longer implicitly scoped to software engineering. At minimum, the terms added
   ad hoc on 2026-08-19 (stakeholder management, project planning, instructional design,
   cross-functional collaboration, problem solving, strategic consulting, Microsoft
   Office/Google Workspace) move into the versioned file as its first non-engineering entries.
3. `_PREFERRED_SECTION_MARKERS`/`_REQUIRED_SECTION_MARKERS` gain non-English markers, starting
   with Spanish and Portuguese ("se valorará", "requisitos", "diferenciais", etc.) — a posting
   written in the language it's hiring for should have its own preferred/required structure
   recognized.
4. `LANGUAGE_TERMS` gains each language's own native name(s) as a synonym (e.g. "inglés" for
   english, "español" for spanish, "alemán" for german, "português" for portuguese, "français"
   for french) — this session added inglés/español/alemán; português/français and others remain.
5. A regression test fixture captures the Lidl (Spain) posting's requirement set from
   2026-08-19 (redacted of any personal data) so today's fix is a tested fixture, not tribal
   knowledge lost to a comment.
6. Criterion 14's determinism (scoring has no LLM call) is unaffected — this spec only widens
   what the deterministic extractor recognizes, it doesn't change how matching scores requirements.

## Out of scope

- Graduating extraction to an LLM-assisted step (spec 001's open question 4 proper) — a bigger,
  separate decision that trades determinism for coverage; this spec keeps the dictionary
  approach and just makes it honest about non-English, non-engineering postings.
- Any change to `matching/matcher.py`'s scoring formula or `generation/validator.py`'s
  anti-fabrication checks.
- A locale-formatting bug found in the same session: `generation/validator.py`'s numeric-claim
  check (`_check_numeric_claims`/`_token_matches_haystack`) does exact substring matching
  between a generated numeric token and the source bullet's `metric` field, so Spanish/German
  typographic conventions (a space before `%`, e.g. "100 %" vs a stored "100%") produce false
  rejections. Worked around today by adding space-variant text to affected bullets' `metric.baseline`
  in `data/profile.yaml`, not by touching the validator — the anti-fabrication path is
  safety-critical and deserves its own careful spec, not a same-session patch. Worth a dedicated
  follow-up: normalize whitespace before comparing numeric tokens, or accept a documented list of
  locale-specific unit-spacing variants.

## Open questions

1. Should the term list be hand-maintained centrally (works fine for this single-user tool per
   spec 001 criterion 35), or should canonical skill keys be derived automatically from
   `data/profile.yaml`'s own skill names at ingestion time — less duplication, but couples
   ingestion to the profile schema in a new way.
2. Should a fresh `data/profile.yaml` (a new user forking this harness) ship with a starter
   term list matched to *some* common non-engineering professions, or is "grow it from your own
   first real posting" the intended, acceptable workflow (consistent with how the PT-PT term
   list is meant to grow)?

## Sign-off

- [ ] Human has read this and understands the *why*, not just the *what*.
- [ ] Acceptance criteria are specific enough to write failing tests from.

*(Implementation does not start until this box is checked — today's ad hoc widening in
`requirements.py` is a stopgap authorized directly by Gustavo for the one real run, not a
substitute for this spec's sign-off.)*
