# PR body — spec: CV Writer (001)

Ready to paste into GitHub once a remote exists. Follows `.github/pull_request_template.md`.
Branch: `spec/001-cv-writer` → `main`. Title: `spec(001): CV Writer — signed-off feature spec`.

---

## What & why

Adds the first feature spec to this harness: [`specs/features/001-cv-writer.md`](../../specs/features/001-cv-writer.md) — a **CV Writer** that turns a job posting into a truthful, well-matched CV in minutes, and keeps a queryable track record of every application sent.

This PR is **documentation only**. No `src/` code, no test runner, no dependencies. It exists because `CLAUDE.md` gates implementation behind a human-signed-off spec, and this is that gate being walked through properly rather than skipped on the first feature.

The *why*, in one line: a generic CV gets filtered out and a genuinely tailored one costs an hour, so the choice today is between few good applications and many weak ones. Structuring experience once — job histories as STAR stories with numbers attached — makes tailoring cheap, inspectable, and repeatable.

Three design decisions in the spec are worth reviewing specifically, because they are the ones that will be expensive to change later:

1. **The LLM only rephrases; it never decides.** Match scoring and evidence selection are deterministic and LLM-free (criterion 14). The model rewrites already-selected, already-true bullets (18). This is what keeps the pipeline unit-testable and offline-testable at all.
2. **"Don't fabricate" is a validator, not a prompt.** Every generated bullet carries the id of the profile bullet it came from; criterion 19 rejects unsourced bullets, employers/dates/credentials absent from the profile, and numeric claims not present in the source metrics.
3. **The core knows nothing about the web.** The UI is the primary interface, but criterion 34 forbids web-framework imports in the domain modules, so tests for the whole feature never boot a server and the "scale it later" ambition stays open without building for it now.

Also adds the pairing log for the session that produced it: [`pairing/sessions/2026-08-17-cv-writer-spec.md`](../../pairing/sessions/2026-08-17-cv-writer-spec.md) — including the recommendation the human overrode (CLI-first → web UI) and the five revisions from the review round.

## Acceptance criteria covered

**None** — by design. This PR delivers the criteria; it implements none of them. 37 criteria in eight groups (profile/skills store → posting ingestion → matching → generation, language, anti-fabrication → output → track record → web UI → repo hygiene), each mapped to a `tests/` location in the spec's criterion→test table, and sliced into five TDD-ordered deliveries.

The first implementation PR will cover **criteria 1–5** (profile core: schema validation, STAR bullets, per-history quantified metrics, skill-to-evidence links). No database, no UI, no LLM in that slice.

## Learning notes (optional, encouraged)

- **Renumbering was free, and that is the whole argument for spec-first.** The review round changed enough that criteria went from 31 to 37. Because no tests existed yet, nothing had to be re-pointed. The same five corrections landing after slice 3 would have meant rewriting tests and code.
- **A quota can cause the problem it was meant to prevent.** The draft required a metric on every bullet; the review moved it to at least one per job history. Demanding a number everywhere pressures whoever fills the profile — human or model — into inventing precision, which is exactly what the anti-fabrication validator exists to catch.
- **The best test for a formatting rule is often indirect.** Rather than asserting fonts and margins, criterion 26 extracts the rendered PDF's text and compares it to the Markdown source: if the layout is ATS-hostile (multi-column, layout tables, text in images), that extraction is what breaks.
- **One heavy dependency, two features.** Headless Chromium was chosen for PDF rendering, then turned out to be the right answer for ingestion tier 2 (rendering JS-heavy postings) too. Noted in open question 2, which still wants a WeasyPrint spike before the choice is locked in an ADR.
- Still fuzzy, and tracked as open questions rather than pretend-answered: how good plain phrase-matching will be at extracting requirements from real postings (4), and how far a `brasileirismos` term list can carry PT-PT quality before a native-speaker read becomes the real acceptance test (5).

## Checklist

- [x] Spec in `specs/features/` is signed off — `001-cv-writer.md`, status `signed-off`, both boxes checked by the human on 2026-08-17 after the revisions in its revision log
- [x] Tests written before implementation (TDD) — n/a, docs-only PR; the spec's criterion→test table is what the first tests will be written from
- [ ] CI passing — **blocked, see below**
- [x] No secrets committed (see `docs/security.md`) — docs only; the spec explicitly forbids persisting `ANTHROPIC_API_KEY` (criterion 23) and requires `data/` to be gitignored before any real profile exists (31)
- [x] Pairing notes added to `pairing/sessions/` if this was a paired session

### Reviewer: three things to settle in this PR

1. **The default branch is `master` locally, but `.github/workflows/ci.yml` triggers on `main`, and `CLAUDE.md`/`README.md` both say PRs target `main`.** As it stands, CI would never run. Rename the branch (`git branch -m master main`) or change the workflow triggers — pick one before this merges, otherwise the checklist item above stays unfixable.
2. **No git remote and no `gh` CLI in this environment**, so this PR could not be opened from the session that wrote it. Creating the GitHub repo, connecting `CODEOWNERS` to real usernames, and enabling branch protection on `main` (required check + one review, per `docs/security.md`) are the deliberate manual steps.
3. **`.gitignore` does not yet cover `data/`.** Nothing personal exists yet, so nothing is at risk today — but the guard should land before the profile does. Cheapest as part of this PR or the first line of slice 1.
