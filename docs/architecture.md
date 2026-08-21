# Architecture

Two layers live in this repo: the **harness** (how work gets done here) and **cv-writer** (the
application it has been building). They are separable on purpose — the harness is what you fork
into the next project.

## The harness

`docs/harness-engineering.md` is the full account of why it is shaped this way. In brief:

| Pillar | Artifacts |
|---|---|
| Feed-forward | `CLAUDE.md`, `AGENTS.md`, `.claude/skills/spec-driven/`, `.specs/features/*/spec.md`, this file |
| Sensors | `scripts/*.py`, `tests/`, the hooks in `.claude/settings.json`, `.github/workflows/ci.yml` |
| Memory | `.specs/STATE.md`, `.specs/LESSONS.md`, `.specs/features/*/tasks.md`, `pairing/sessions/` |
| Bootstrap | `scripts/bootstrap_context.py` + the `SessionStart` hook |

Mission separation lives in `.claude/agents/`: `spec-author` and `architect` on the
high-reasoning tier, `implementer` and `verifier` on the code tier, `scaffolder` and
`pair-scribe` on the fast tier. `implementer` cannot write `validation.md`; `verifier` cannot
touch `src/` or `tests/`. That mutual exclusion is what makes "author ≠ verifier" structural
rather than aspirational.

## cv-writer

Turns a job posting into a truthful, well-matched CV. Full requirements:
`specs/features/001-cv-writer.md` (criteria 1–37). Decisions: `specs/adr/0001`–`0005`.

```
src/cv_writer/
├── profile/      the single source of truth about the candidate — every write goes through here
├── db/           SQLite track record + SQL migrations (ADR 0002)
├── ingestion/    job-posting fetch and parse; tier 2 uses Playwright for JS-rendered pages
├── matching/     deterministic, inspectable posting-requirement → profile-evidence matching
├── generation/   CV rendering, language handling, and the anti-fabrication guarantees
└── web/          FastAPI + Jinja UI, localhost-bound, single user (ADR 0005)
```

### Boundaries that are enforced, not just described

- **Core must not import the web layer.** `tests/unit/web/test_core_has_no_web_imports.py` walks
  the AST and fails the build if it does. Copy this pattern for any new boundary — a boundary
  with no test is a preference.
- **Templates autoescape.** `tests/unit/web/test_template_autoescaping.py`. Jinja's
  `select_autoescape()` defaults to `("html", "htm", "xml")` and these templates are named
  `*.html.jinja`, so the default would have silently rendered everything unescaped
  (`.specs/LESSONS.md` L-001).
- **Downloads cannot escape the output directory.** `tests/unit/web/test_download_guard.py`.
- **The server binds localhost only.** `tests/unit/web/test_localhost_binding.py`.

### The rule that looks like a bug

A generation *refusal* is the product working. cv-writer will not invent experience the profile
does not contain. Never loosen a guard to make generation succeed — fix the profile data it was
refusing to invent (`.specs/LESSONS.md` L-003).

## Testing

`tests/` mirrors `src/` 1:1 — `unit/` (fast, isolated), `integration/` (real SQLite temp files,
real Chromium, local fixture pages), `e2e/` (full UI walk via the FastAPI test client). Every
test cites the criterion it proves.
