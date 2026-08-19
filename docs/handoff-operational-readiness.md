# Handoff: getting CV Writer operational for real runs

**For:** a planning agent picking this up cold.
**Date:** 2026-08-19
**Repo:** `C:\g\projetos` (Windows, PowerShell primary). Read `CLAUDE.md` first — its hard rules
bind you, especially **never delete anything without fresh explicit human permission**.

## Where things stand

All five delivery slices of `specs/features/001-cv-writer.md` are merged. `main` is at `3f80958`
(slice 5 — web UI + CI, criteria 32–37). CI is green; 277 tests pass; `ruff check src tests` clean.

The application **runs**: `python -m cv_writer.web` serves on `http://127.0.0.1:8000`, verified
returning 200 on `/` and `/applications`, bound to loopback only. Chromium is installed and
working (151.0.7922.34). The SQLite track record at `data/cv_writer.sqlite3` exists and
self-migrates.

**The software is done. What remains is not code — it is data and configuration.** The tool
cannot yet produce a truthful CV for a real person, because it has no real person in it.

## The goal

Get the tool to the point where the maintainer (Gustavo) can put a real job posting in one end and
get a truthful, well-matched CV out the other — one he would actually send.

## Blockers, in order

### 1. `data/profile.yaml` contains fake data — this is the whole job

It is currently a verbatim copy of `data/profile.example.yaml`: "Ana Example", 2 job histories,
2 skills, all fictional. Every CV generated until this is replaced is a CV for a person who does
not exist.

This file is **hand-authored by design**. The spec explicitly rules out parsing existing CV
PDFs/DOCX or importing a LinkedIn export ("parsing is unreliable and would be a feature of its
own"). It is seeded by rereading old CVs, not extracted from them.

Schema is `src/cv_writer/profile/models.py`. Top-level keys: `identity`, `languages`, `education`,
`job_histories`, `skills`. The constraints that will reject a careless draft, and why they exist:

- **3–5 STAR bullets per job history**, each with explicit `situation` / `task` / `action` /
  `result` fields (criterion 3).
- **At least one quantified metric per job history — not per bullet** (criterion 4). This
  asymmetry is deliberate and worth preserving in any tooling built around it: forcing a number
  onto every bullet invites invented precision, which is the exact failure criterion 19 exists to
  catch. Individual bullets may be qualitative; a *history* with no metric anywhere fails
  validation.
- **`metric.value` is a verbatim string**, not a parsed number — `"+37%"`, `"R$1.2M"`,
  `"45min -> ~2min"` do not share one numeric shape.
- **Skills link to the job histories that evidence them** (criterion 5). A skill with no
  evidencing history still loads, but `profile_check()` reports it as unevidenced.
- Bullet and history `id`s must be stable and not purely numeric.

Validate after each edit:

```powershell
python -c "from cv_writer.profile import load_profile; load_profile('data/profile.yaml')"
```

Errors name the offending field and its path, and never yield a partially-loaded profile.

Also run the non-fatal check for weak spots (unevidenced skills; histories where only one of
several bullets is quantified):

```powershell
python -c "from cv_writer.profile import load_profile, profile_check; [print(w) for w in profile_check(load_profile('data/profile.yaml'))]"
```

`data/profile.yaml` is gitignored (`.gitignore:36`, `data/*`) because it holds real contact details
and employment history. **It must never be committed.** `data/profile.example.yaml` is the only
profile-shaped file that belongs in version control.

No restart is needed after editing — `src/cv_writer/web/routes.py:73` reloads the profile on every
request. Save and refresh.

### 2. `ANTHROPIC_API_KEY` is not set — RESOLVED (2026-08-19)

Only the generation step needs it. Ingestion, requirement extraction, matching, the gap report,
and the track record all work without it — the match report is deterministic and involves no LLM
call at all (criterion 14).

The first real run required exporting the key by hand every session. `web/__main__.py`'s `main()`
now calls `load_dotenv()` (python-dotenv) before starting the server, so a gitignored `.env` file
is picked up automatically — no more manual `$env:` step:

```powershell
copy .env.example .env
# then edit .env and uncomment/fill in ANTHROPIC_API_KEY=sk-ant-...
python -m cv_writer.web
```

Per `docs/security.md` and criterion 23: environment only, read at call time by
`ClaudeRephraser`, never written to disk, the database, or a generated artifact. `load_dotenv()`
only populates `os.environ` from the gitignored `.env` — it doesn't change how or when the key is
read. **Never put it in a committed file**, and never pass it as an inline command-line argument.

### 3. First real end-to-end run has not happened

Everything to date has run against fixtures. Two things are genuinely unproven against reality:

- **URL ingestion against a live posting.** Tiers 1→2→3 are tested against local fixture pages
  served on localhost, never live sites. The escalation behaviour on a real job board is unknown.
- **The URL form's upfront field collection.** The implementing agent chose to collect
  company/country/area/role on the URL form as well as the paste form, because `Posting.company`,
  `.role_title` and `.country` are optional and usually `None` for a fetched posting, while the
  draft needs all four to build a match report or an `Application`. This is the one design call
  made outside the ADR and is flagged in PR #5's "Reviewer: worth a look". It deserves a check
  against a real posting URL.

## What "operational" looks like — verification

1. `data/profile.yaml` holds real data, loads clean, and `profile_check()` reports nothing the
   maintainer disagrees with.
2. A real posting URL ingests successfully, or fails with a reason that makes the paste fallback
   an obvious next move (criteria 9.3, 11 — it must never silently proceed on empty or truncated
   text).
3. The match report's score, formula, and gap list are inspectable and defensible.
4. A generated CV passes the anti-fabrication validator and, if PT-PT, the `brasileirismos`
   checker — or is refused with a reason naming the offending line.
5. Markdown, PDF, and plain text download; the PDF's extracted text matches the Markdown source.
6. The run appears in `/applications` and is findable by combined filters (e.g. skill = Python AND
   country = Portugal, sorted by date descending).

## Things a planner should know before proposing changes

- **A generation refusal is the feature working, not a bug.** The validator rejects a bullet with
  no source id, an employer/title/date/credential absent from the profile, or a numeric claim not
  present in its source bullet's metrics. It refuses outright to write in a language not listed in
  the profile at working proficiency. Do not plan around these; plan to surface them well.
- **PT-PT and PT-BR are distinct targets** (criterion 21). The `brasileirismos` checker is a
  versioned, data-driven YAML term list at `src/cv_writer/generation/data/pt_pt_terms.yaml`,
  extendable without touching code. Growing that list is the intended response to a miss.
- **The profile is the single write path.** `data/profile.yaml` is authoritative; the database copy
  is derived and rebuildable. Editing the profile through the UI would break that — it is spec
  open question 3 and remains deliberately unimplemented.
- **Known, accepted limitations** (documented in code, not oversights): `output_paths.py` checks
  path existence without reserving it, so two concurrent generation runs could collide; `/confirm`
  has no double-submit idempotency guard; there is no rollback between writing artifacts and
  inserting the DB row. All three are scoped away by the tool's single-user localhost design and
  should only be revisited if that scoping changes.
- **Open questions the spec never closed** (`specs/features/001-cv-writer.md`, "Open questions"):
  outcome tracking (interview/rejected/offer) as a nullable `status` column; whether requirement
  extraction graduates to an LLM step that is human-confirmed; whether a native-speaker read of the
  first PT-PT CVs becomes the acceptance test for the term list. Any of these is a candidate for
  the next spec.
- CI has no `timeout-minutes`. One run wedged 5+ hours on `playwright install chromium --with-deps`
  before being cancelled manually; a rerun of the same commit passed in 2m10s. Adding a job timeout
  would turn a future stall into a fast red instead of a hung run.

## Working agreement

`CLAUDE.md` governs. In particular: a feature starts as a spec in `specs/features/` with human
sign-off before implementation; tests come before code; a human reviews the diff before merge; and
nothing is deleted without fresh explicit permission for that specific action.
