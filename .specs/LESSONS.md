# LESSONS

Rules that would have prevented a real gap found in this repository. Agent-facing and terse —
**load this before Specify and before Execute.**

This is not a diary. `pairing/sessions/` holds the human-facing narrative of how a decision was
reached; `docs/learning-log.md` holds what the maintainer learned. A line only belongs here if it
would change what an agent *does* next time.

Format: `L-NNN — <rule>. **Because:** <the actual failure that produced it>.`

---

- **L-001** — Check a library's *default* argument values before relying on them, not just its
  signature. **Because:** `jinja2.select_autoescape()` defaults `enabled_extensions` to
  `("html", "htm", "xml")`, and this project's templates are named `*.html.jinja` — every
  template would have rendered unescaped. Caught by reading the default, not by a test.
  (slice 5, `pairing/sessions/2026-08-18-slice5-web-ui-ci.md`)

- **L-002** — When tests drive a handler directly, they do not prove the form that reaches it can
  produce those inputs. **Because:** an HTML `<input type="checkbox">` sort control could never
  submit `descending=false` — unchecked checkboxes submit nothing at all. The tests passed because
  they set query params themselves. Test the surface the user actually touches.
  (slice 5, same session)

- **L-003** — A generation *refusal* is this application working correctly, not a bug. **Because:**
  cv-writer's anti-fabrication guarantee is the product. Never "fix" a refusal by loosening the
  guard; fix the profile data it was refusing to invent.
  (`docs/handoff-operational-readiness.md`)

- **L-004** — Vocabulary lists built from one language and one domain fail silently on real input,
  returning few results rather than an error. **Because:** `SKILL_TERMS` was entirely
  English software-engineering vocabulary, so a Spanish retail posting extracted exactly one
  requirement and nothing flagged it. Prefer a loud failure over a quiet empty result.
  (`.specs/features/002-requirement-dictionary-expansion/spec.md`)

- **L-005** — CI steps that pull the network need a timeout. **Because:** a `playwright install`
  step wedged for more than five hours before being cancelled by hand; the job had no
  `timeout-minutes`. An unbounded step is not a sensor, it is a hang.
  (`docs/handoff-operational-readiness.md`)
