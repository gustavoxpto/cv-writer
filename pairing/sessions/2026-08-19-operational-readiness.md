# 2026-08-19 — Operational readiness: first real end-to-end run

## Goal

Slices 1-5 of `specs/features/001-cv-writer.md` were merged and CI-green (`docs/handoff-
operational-readiness.md` is that handoff note), but nobody had run the tool against a real job
posting yet. This session did that — a real Spanish "Lidl" posting — to find out what an
end-to-end run actually surfaces that unit/integration tests, which never touch a real posting
or a real LLM call, can't.

## Tried

- **Requirement extraction against a real, non-engineering, Spanish posting.** `SKILL_TERMS` and
  friends in `ingestion/requirements.py` turned out to be 100% English, software-engineering
  vocabulary — a leftover from spec 001's "Ana Example, Backend Engineer" persona. Against a
  Spanish retail-consulting posting, extraction found almost nothing to match against. Fixed ad
  hoc, in place, additive-only (new dict keys/list entries, no logic changes) — authorized
  directly for this one run rather than blocking on a full redesign. `specs/features/002-
  requirement-dictionary-expansion.md` is the follow-up spec for the durable version (a
  versioned YAML term file, mirroring how `pt_pt_terms.yaml` already does this for the PT-PT
  checker) — draft, unsigned, implementation not started.
- **Generating the actual CV.** Two more problems surfaced here, not covered by 002:
  1. `ANTHROPIC_API_KEY` had to be exported by hand (`$env:...`) every session — no automatic
     loading existed. Small, no acceptance-criterion impact (criteria 22/23 only require the key
     be read from the environment at call time, which still holds either way) — fixed directly
     this session, no spec needed.
  2. The generated CV came out with English section headings ("Experience"/"Education"/
     "Skills") but Spanish bullet content — a half-translated document. Traced to `generation/
     render_text.py::render_markdown()` hardcoding the English headings literally; only bullets
     pass through the LLM rephraser with a target language. Compounded by a second bug:
     `generation/language.py::resolve_output_language()`'s `override` parameter was checked only
     against the profile's proficiency, never against `SUPPORTED_LANGUAGES` — so a Spanish
     override sailed through as "allowed" even though Spanish wasn't (and isn't yet) a language
     the tool has any real structural support for.
- **A third, separate bug found but not fixed here**: `generation/validator.py`'s numeric-claim
  check does exact substring matching, so locale-specific spacing (e.g. "100 %" vs "100%")
  produces false rejections. Worked around for this one run by editing `data/profile.yaml`
  (gitignored, not part of any diff) rather than touching the validator. Flagged in spec 002's
  "Out of scope" as needing its own dedicated spec — not attempted here.

## Decided

- The API-key fix ships directly (`python-dotenv`, `load_dotenv()` in `web/__main__.py::main()`
  before the server starts) — dev-ergonomics, no criterion changes, no spec needed.
- The heading/language bug does **not** ship as a quick patch, even though the override-bypass
  half of it is arguably just restoring criterion 20's existing intent. The heading-localization
  half genuinely reinterprets criterion 26, which literally names "Experience, Education,
  Skills" — English words — as an ATS-safety requirement. Per CLAUDE.md's hard rule (spec before
  code, not optional), that's a new spec: `specs/features/003-full-document-language-
  localization.md`, written and reviewed for sign-off before any code changes land, rather than
  reasoning through the criterion-26 conflict unilaterally mid-fix.
- Spanish becomes a real 4th supported language (`SUPPORTED_LANGUAGES`, detection, headings,
  profile-proficiency gate) as part of spec 003's scope, rather than just being cleanly refused
  — that's what the actual Lidl posting needed, and "refuse it" would just defer the same
  problem to the next non-English posting.
- The `requirements.py` stopgap and spec 002's draft are committed as-is this session (commit-
  ready per review: additive, well-commented, template-conformant draft with both sign-off boxes
  correctly still unchecked) — committing a draft spec isn't the same as approving its
  implementation, that gate is still its own sign-off checkbox.

## Learned

(Build-to-learn framing) The clearest thing this session demonstrated: unit and integration
tests that stub out the LLM and the real posting (which is the right call for speed and
determinism — see criterion 22) can't catch a bug like the heading/language one, because the
bug is precisely in the part of the pipeline that never touches the LLM at all
(`render_text.py`'s literal strings). A green test suite and a working real run are different
claims. The fix isn't "test more of the real path in CI" (that would reintroduce the network
dependency the architecture deliberately avoided) — it's noticing that "generate a real CV and
actually read it" is a distinct verification step from "the test suite passes," and doing it at
least once before calling a slice operationally ready.
