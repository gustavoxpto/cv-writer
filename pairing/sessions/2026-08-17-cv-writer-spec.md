# 2026-08-17 — CV Writer: first feature spec

## Goal

Write the pre-implementation requirements doc for the harness's first real feature: a CV Writer
that matches real experience and skills against a specific job opening, fast, and keeps a
queryable track record of every CV sent. Result: `specs/features/001-cv-writer.md` (draft,
awaiting human sign-off).

## Tried

- **Read the harness first, then asked rather than assumed.** Four decisions were genuinely
  undecidable from the repo (`src/` is empty, no language chosen), so they were put to the human
  as options with trade-offs instead of being picked silently: interface/stack, tailoring engine,
  profile data source, output format.
- **CLI-first was the AI's recommendation and was rejected.** The reasoning for a CLI was smaller
  surface area and easier TDD. The human overrode it: the tool has to *look* usable when
  demonstrated to a non-technical audience, and should be able to grow beyond one user. Accepted —
  with a structural mitigation rather than a compromise on the choice (criterion 28: all domain
  logic in importable modules with zero web-framework imports, so tests for the core never boot a
  server and a different front-end stays possible).
- **"Let the LLM write the CV" was considered and narrowed.** Sending profile + posting to Claude
  and taking the output is the highest-quality prose path, but it is untestable in a TDD repo and
  it is the exact shape that invents employers and numbers. Rejected in favour of hybrid: the
  match score and evidence selection are deterministic and LLM-free (criterion 12); the LLM only
  rephrases already-selected, already-true bullets (criterion 16).
- **Parsing old CVs / LinkedIn export into the profile was scoped out.** PDF and DOCX CV parsing
  is unreliable and would become its own feature; the human authors `data/profile.yaml` by hand,
  seeded by rereading old CVs, plus per-application custom input.

## Decided

- Spec at `specs/features/001-cv-writer.md`, 31 numbered acceptance criteria, sliced into 5
  TDD-ordered deliveries. Slices 1–2 (profile core, database) carry no LLM at all — the LLM
  arrives in slice 4, *after* the validator that can reject its output exists.
- Stack: Python 3.12 + FastAPI/Jinja server-rendered UI + SQLite + pytest/ruff; Markdown as the
  versionable CV source, rendered to PDF, plus a plain-text ATS variant. To be recorded as an ADR
  before code — the spec deliberately does not stand in for that record.
- Two requirements the human added mid-session, now first-class in the spec: job histories are
  stored as **STAR** bullets (3–5 per role, structured `situation`/`task`/`action`/`result`), and
  every `result` must carry a **quantified metric** as structured data — both enforced by
  validation (criteria 3–4), not by good intentions.
- Skills are records linked to the histories that evidence them (criterion 5), so the database is
  a cross-referencing store for reuse, not just an archive.
- Anti-fabrication is an engineering requirement with a test: every generated bullet carries the
  source id it derived from, and a validator rejects unsourced bullets, unknown employers/dates,
  and numbers absent from the source metrics (criterion 17).

## Review round (same session, human read the draft)

Five changes came back, all of them tightening the spec rather than expanding it:

- **Metrics per job history, not per bullet.** The draft demanded a number on every bullet. The
  human's correction is the better engineering call, not just the easier one: a per-bullet quota
  pressures whoever fills the profile — or the model rephrasing it — into inventing precision,
  which is the exact failure criterion 19 exists to catch. Per-history keeps "this role has proof"
  as a real claim. `profile check` still nudges (warns, doesn't fail) when only one bullet in a
  role is quantified.
- **URL fetch now escalates instead of surrendering.** Tier 1 plain HTTP → tier 2 real headless
  browser (wait for network idle, scroll for lazy content, accept the cookie banner, expand "see
  more", read the *rendered* text, unhurried) → tier 3 paste. Two notes: this makes the Chromium
  dependency pay for two features, since PDF rendering already needed it; and the boundary is
  written into the spec as criterion 10 — tier 2 only reads what a signed-out human could read in
  their own browser, and stops at logins, CAPTCHAs, and explicit blocks rather than working around
  them. "Slow and human-paced" is about rendering JS-heavy pages properly, not about disguise.
- **PDF rules made concrete and therefore testable.** Black on white, single column, no
  layout tables or content in graphics, standard headings, a documented shortlist of widely
  available fonts, embedded, 10pt minimum. The clever part is criterion 26's last line: the actual
  test is extracting the PDF's text and comparing it to the Markdown source — if the layout is
  ATS-hostile, that extraction is what breaks.
- **Open question 2 resolved: language follows the posting**, and PT-PT is a different target from
  PT-BR. This became criterion 21: a versioned, data-driven list of `brasileirismos` (lexis like
  *celular*/*telemóvel*, *equipa*, *ficheiro*, *ecrã*; *estar a + infinitivo* vs BR *estar +
  gerúndio*; clitic placement) that blocks acceptance and names the replacement. Deliberately a
  deterministic checker, not a prompt instruction — it is a pure function over text, testable with
  no model, and written *before* the LLM is wired up in slice 4. Criterion 20 also refuses to
  generate in a language the profile doesn't claim at working proficiency: no CV in a language you
  can't hold the interview in.
- **Open question 5 resolved: one page is the target, two the exception, the human decides.** The
  tool proposes two pages when requirements genuinely exceed one and shows what a one-page cut
  would drop; it never silently changes page count to make content fit.

Criteria renumbered 31 → 37. Safe to renumber precisely because no tests exist yet — which is the
cheapest moment for a spec to change, and an argument for the spec-first order.

Spec signed off by the human after these revisions; slice 1 (profile core) is now unblocked.

## Learned

- **Where the LLM sits determines whether the system is testable.** The same feature is either
  fully unit-testable or barely testable depending on whether the model *decides* things or only
  *rephrases* decided things. Putting it behind one interface with a fake implementation
  (criterion 18) is what lets the whole pipeline run offline in CI with no API key.
- **"Don't hallucinate" is not a prompt, it's a validator.** Asking a model to stay truthful is a
  wish; requiring every output line to trace to a source id and diffing numeric claims against
  stored metrics is a test that fails.
- **Derived vs authoritative data.** `data/profile.yaml` is the write path; the SQLite copy is
  rebuildable from it. Naming which store is the truth *before* writing code avoids the classic
  two-sources-of-truth drift — and open question 1 flags that editing the profile through the UI
  would break exactly that invariant.
- Still fuzzy: how good plain phrase-matching will actually be at pulling requirements out of real
  postings (open question 4 in the spec), and how far a term/pattern list can carry PT-PT quality
  before it needs a native-speaker read as the real acceptance test (open question 5).
