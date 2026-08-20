# .specs/

**Agent-facing working memory.** What is being built, what was agreed, where work stopped.

`STATE.md` is the file to read first, every session — `scripts/bootstrap_context.py` prints its
essentials automatically at `SessionStart`.

```
.specs/
├── STATE.md          ## Current (live feature + phase) · ## Decisions (AD-NNN, append-only)
│                     ## Handoff (snapshot) · ## Bypass log
├── LESSONS.md        L-NNN rules that would have prevented a real gap here
├── test-census.json  the test-count ratchet's baseline
├── templates/        spec · design · tasks · contract · validation
└── features/<NNN-slug>/
    ├── spec.md       Why + EARS criteria (AC-NNN) + human sign-off        [always]
    ├── design.md     shape, boundaries, decisions                          [large/complex only]
    ├── tasks.md      atomic tasks (T-NNN), each tracing to a criterion     [>3 steps]
    ├── contract.md   agreed outcomes (C-NNN), verifier-signed              [always]
    └── validation.md verifier's report: PASS/FAIL, evidence, sensor        [always]
```

**Lazy creation.** A file exists only once its phase produced content. The absence of
`design.md` is the signal that Design was correctly skipped for a small feature — not that
someone forgot. Do not create empty artifacts to look thorough.

## Where the older specs live

`specs/` (no dot) still holds:

- `specs/features/001-cv-writer.md` — signed off, implemented across five merged PRs, and
  cross-linked from six `docs/pr/*` files, five ADRs and six pairing notes. Frozen in place as a
  historical record. See `AD-001` in `STATE.md`.
- `specs/adr/` — the home for heavyweight architecture decisions. Still current, still where
  ADRs go. `STATE.md`'s `## Decisions` holds only the light ones and links out for the rest.
  One decision, one home.
- `specs/templates/spec-template.md` — superseded by `.specs/templates/spec.md`, kept as a
  pointer.

Everything new goes in `.specs/`.

## Validating

```
python scripts/validate_spec.py     .specs/features/<slug>/spec.md
python scripts/validate_tasks.py    .specs/features/<slug>/tasks.md
python scripts/validate_contract.py .specs/features/<slug>
python scripts/validate_state.py    <slug>
```

`python scripts/gate.py build` runs the first three across every feature at once, and CI's
`harness` job runs them on every PR.
