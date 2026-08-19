# Spec: Full-document language localization

- **Status:** signed-off
- **Author:** AI (operational-readiness follow-up session) + Gustavo, 2026-08-19
- **Date:** 2026-08-19 (signed off same day)

## Why

The first real end-to-end run (2026-08-19, a Spanish "Lidl" posting) produced a CV with English
section headings ("Experience"/"Education"/"Skills") but Spanish bullet content — a
half-translated document nobody would actually send. Root cause, traced in code:

- `generation/render_text.py`'s `render_markdown()` (lines 26, 31, 36) hardcodes the literal
  English words `"## Experience"`, `"## Education"`, `"## Skills"`. Only `cv.accepted_bullets`
  passes through the LLM rephraser with a target language (`rephraser.py`'s `_build_prompt()`,
  "in {request.target_language}{variant_note}") — headings are never translated.
- Separately, `generation/language.py`'s `resolve_output_language()` accepts any `override`
  string and checks it only against the profile's `languages`, never against
  `SUPPORTED_LANGUAGES` (the set `detect_posting_language()` actually knows how to detect). An
  override naming a language the tool has no other support for — e.g. `"spanish"`, not in
  `SUPPORTED_LANGUAGES` today — sails through as `allowed=True` as long as the profile lists it
  at working proficiency, even though nothing downstream except the rephraser prompt actually
  knows how to render that language's structure. This is a bypass of criterion 20's real intent
  ("the CV is written in the posting's language") for everything except the bullet text itself.

Criterion 20 (spec 001) is silent on whether "the CV" means bullets only or the whole document;
the original implementation's reading landed on bullets-only. Criterion 26 additionally names
"standard section headings (Experience, Education, Skills)" as part of the ATS-safety checklist
— read literally, that wording mandates the English words even when the rest of the document is
in another language, which is itself the bug's other root cause and needs amending.

The Lidl posting that surfaced this was Spanish, and Spanish isn't a supported language at all
today (`SUPPORTED_LANGUAGES` has only english/portuguese/german) — so this spec also adds it as
a fourth supported language, rather than just closing the override bypass and leaving Spanish
postings refused.

## What (acceptance criteria)

1. `resolve_output_language()`'s `override` parameter is validated against `SUPPORTED_LANGUAGES`
   before anything else. An override naming a language not in `SUPPORTED_LANGUAGES` is refused
   (`allowed=False`) with a reason distinct from the existing "not in profile" / "below working
   proficiency" reasons — e.g. "'\<language\>' is not a language this tool can generate
   structural content in" — restoring criterion 20's intent that the language decision is real,
   not just profile plumbing.
2. Spanish becomes a fourth entry in `SUPPORTED_LANGUAGES` (`generation/language.py`), alongside
   english/portuguese/german, with its own curated stopword set for
   `detect_posting_language()` — detected the same flat way english/german already are (no
   PT-PT/PT-BR-style variant mechanism; Spanish does not need one for this spec).
3. Spanish participates in the normal profile-proficiency gate exactly like the other three
   languages (`_check_profile_supports()` / `MINIMUM_WORKING_RANK`) — no special-casing.
4. The tool's own hardcoded structural strings — at minimum the section headings "Experience",
   "Education", "Skills" in `render_text.py`'s `render_markdown()` — are localized to the
   resolved output language, for all four supported languages (English, Portuguese, German,
   Spanish). `render_plain_text()` (which derives from `render_markdown()`) inherits this for
   free.
5. Criterion 26 of `specs/features/001-cv-writer.md` is amended: "standard section headings
   (Experience, Education, Skills)" is reworded to read as an illustrative English example of
   the ATS-safe *pattern* (a small number of clearly-labelled, consistently-named sections — not
   decorative or ambiguous headings), not a mandate to always render literally those English
   words regardless of output language. Recorded as an explicit amendment in spec 001's own
   revision log, since spec 001 is `Status: signed-off` — this is amending a signed spec, not
   silently rewording it.
6. Generation for a language not in `SUPPORTED_LANGUAGES` fails clearly and early (before any
   LLM call), with a reason surfaced to the user through the existing `generate_draft_cv()`
   re-render path (`web/routes.py`) — no route-level changes needed, since that path already
   displays `resolve_output_language()`'s reason generically.

## Out of scope

- The numeric-formatting false-rejection bug in `generation/validator.py` (locale spacing, e.g.
  "100 %" vs "100%") flagged in `specs/features/002-requirement-dictionary-expansion.md`'s "Out
  of scope" — needs its own spec against the anti-fabrication path; not touched here.
- Translating profile-authored content (`profile.education[].degree`/`.institution`,
  `profile.skills[].name`) — see Open questions; the working default is these stay verbatim.
- A PT-PT/PT-BR-style variant mechanism for Spanish — treated as one flat language.
- Localizing anything outside `render_text.py`'s own literal control strings — this is about the
  generated CV artifact only, not the web UI's own English chrome/labels.
- Changing `render_html.py`'s `language` value semantics beyond what's needed to stay consistent
  — it already receives `cv.language` dynamically at both call sites today.

## Open questions

1. Should profile-authored content (education degree/institution names, skill names) also be
   translated, or stay verbatim as the human wrote them? **Recommended default: stay verbatim**
   — translating a person's actual credential/institution names risks fabrication-adjacent
   inaccuracy (criterion 19's anti-fabrication guarantee), and institution names specifically
   usually shouldn't be translated in a real CV. Only the tool's own hardcoded structural
   strings get localized. **Confirmed at sign-off (2026-08-19): stays verbatim**, per the
   recommended default above.
2. Exact heading translations are a draft proposal, not a linguistic authority — same caveat
   spec 001 already carries for PT-PT (native-speaker read listed as a future acceptance test):
   - Portuguese: Experiência Profissional / Formação / Competências
   - German: Berufserfahrung / Ausbildung / Kenntnisse
   - Spanish: Experiencia / Educación / Habilidades
   Worth a native-speaker sanity check before or soon after merge, same as PT-PT's open item.
3. Should `render_html.py`'s `language` value (currently the full lowercase word — "english",
   "portuguese" — used for the HTML `lang` attribute) be normalized to a proper BCP-47 code
   ("en", "pt", "es", "de") for semantic correctness? Not required by any acceptance criterion;
   flagging as a minor, separate nice-to-have, not scoped into this spec.

## Sign-off

- [x] Human has read this and understands the *why*, not just the *what*.
- [x] Acceptance criteria are specific enough to write failing tests from.

Signed off 2026-08-19 by Gustavo. Open question 1 resolved at sign-off (see above); open
questions 2 and 3 remain non-blocking follow-ups.
