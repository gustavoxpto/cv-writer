# Contract: 002-requirement-dictionary-expansion

- **Spec:** `.specs/features/002-requirement-dictionary-expansion/spec.md`
- **Implementer:** main session (orchestrator), inline — under the ~8-task threshold in
  `.claude/skills/spec-driven/SKILL.md`
- **Verifier:** `verifier` (fresh agent, no memory of writing this)
- **Date:** 2026-08-20
- **Size:** medium — Design skipped (no new component boundary; one module and one data file,
  both copying an existing pattern), Tasks inline below rather than in a separate `tasks.md`.

## Signature

- [x] **Verifier has checked this list against `spec.md`** and confirms it covers every
      acceptance criterion, adds nothing outside the spec, and that each **Check** below is
      something a sensor or an inspection can actually decide.

*(Execute does not start until this box is checked. Anything the verifier wants that is not on
this list must go back into the spec first — it does not get added at validation time.)*

*Signed by `verifier`, 2026-08-20.* Checked the struck-C-007 revision against `spec.md` AC-001 through AC-006: coverage is complete (every AC has a contract item whose Check would genuinely discharge it), C-001..C-006 are byte-identical to the version I already reviewed, and the strike left no dangling `C-007`/old-`T-005`/`T-006` references outside the deliberate "Struck before signature" record. `validate_contract.py` and `validate_spec.py` both exit 0. Signing with one reservation carried forward to validation time, not blocking signature now: C-005's provenance Check ("the fixture contains Spanish prose absent from the term file") is verifier inspection, not a pure sensor — inherent to what AC-005a asks for, but the validator should read the fixture itself rather than accept the Check description as self-proving once T-005 is unblocked.

## What will be built

- [x] **C-001** — Requirement vocabulary is loaded at runtime from a versioned YAML data file,
      not from literals in Python. Adding a term becomes a YAML edit and a `version` bump, with
      no code change.
  - **Verifies:** AC-001
  - **Check:** `src/cv_writer/ingestion/data/requirement_terms.yaml` exists and carries an
    integer `version`. `src/cv_writer/ingestion/term_list.py` exposes
    `load_requirement_terms(path=DEFAULT_TERMS_PATH)` returning a pydantic-validated model,
    mirroring `generation/pt_pt_checker.py::load_pt_pt_terms`. Then
    `grep -n 'python\|kubernetes\|se valorará' src/cv_writer/ingestion/requirements.py` returns
    no term-literal line — no vocabulary survives in the module. Tests in
    `tests/unit/ingestion/test_term_list.py`.

- [x] **C-002** — The migration loses no vocabulary. Every canonical key and phrase the Python
      dictionaries held on 2026-08-20 — the 26 original engineering keys and the 8 Appendix A
      keys alike — is present in the YAML file, spelled identically.
  - **Verifies:** AC-002
  - **Check:** `tests/unit/ingestion/test_term_list.py` holds a frozen literal snapshot of the
    four pre-migration dictionaries and the two marker tuples, copied from git revision
    `387d937`, and asserts the loaded file equals it exactly (`==`, not a subset check). A
    separate assertion names the 8 Appendix A keys with their phrases, so a reviewer can see
    AC-002 discharged without diffing a 34-key blob.

- [x] **C-003** — A Spanish or Portuguese posting's own section headings decide required vs
      preferred, as English headings already do.
  - **Verifies:** AC-003
  - **Check:** `tests/unit/ingestion/test_requirement_sections.py` asserts that in a Spanish
    posting with `Requisitos:` and `Se valorará:` headings, a skill under the first is
    `RequirementKind.REQUIRED_SKILL` and a skill under the second is
    `RequirementKind.PREFERRED_SKILL` — and that the preferred one is not also present as
    required. The same two assertions for Portuguese `Requisitos:` / `Diferenciais:`.

- [x] **C-004** — A language named in its own language is recognised as that language.
  - **Verifies:** AC-004
  - **Check:** `tests/unit/ingestion/test_term_list.py` asserts `extract_requirements` maps
    "inglés" to `english`, "español" to `spanish`, "alemán" to `german`, "português" to
    `portuguese` and "français" to `french`, each as `RequirementKind.LANGUAGE`, and that
    `source_phrase` keeps the native spelling including accents rather than the canonical key.

- [ ] **C-005** — The redacted real posting extracts more than one requirement.
  - **Verifies:** AC-005
  - **Check:** the fixture is committed at
    `tests/integration/ingestion/fixtures/posting_es_redacted.txt`;
    `tests/integration/ingestion/test_real_posting.py` asserts `len(result.requirements) > 1`
    and additionally asserts specific expected canonical values, so the test cannot pass on
    noise alone. Provenance per AC-005a: the text is Gustavo's supplied posting with
    employer-identifying detail removed, not written out of Appendix A. The verifier confirms
    provenance by checking the fixture contains Spanish prose absent from the term file, not
    merely the matched phrases.

- [x] **C-006** — Widening what the extractor recognises introduces no model call anywhere on
      the extract-to-score path.
  - **Verifies:** AC-006
  - **Check:** `tests/unit/ingestion/test_no_model_calls.py` walks `ingestion/` and `matching/`
    with `ast.parse`, copying `tests/unit/web/test_core_has_no_web_imports.py`'s approach
    including its dynamic-`import_module` handling, and fails naming the module if either
    package imports `anthropic`. Plus a runtime assertion: with `socket.socket` patched to
    raise, `extract_requirements(...)` followed by scoring the result still completes.

## Tasks (inline — size: medium)

Red, green, refactor, gate, one commit, per task. Gate levels per `.specs/templates/tasks.md`.

- [x] **T-001** — Create the YAML term file and its loader module.
  - **Covers:** AC-001 · **Delivers:** C-001
  - **Files:** `src/cv_writer/ingestion/data/requirement_terms.yaml`,
    `src/cv_writer/ingestion/term_list.py`, `tests/unit/ingestion/test_term_list.py`
  - **Gate:** quick
  - **Done when:** the loader returns a validated model from the shipped file and `version` is
    asserted to be an int, mirroring the pt-PT list's own guard.

- [x] **T-002** — Switch `requirements.py` to the loaded file, with a no-loss snapshot test.
  - **Covers:** AC-001, AC-002 · **Delivers:** C-001, C-002
  - **Files:** `src/cv_writer/ingestion/requirements.py`, `tests/unit/ingestion/test_term_list.py`
  - **Gate:** quick
  - **Done when:** the snapshot test passes against the frozen 387d937 dictionaries and no
    vocabulary literal remains in `requirements.py`.

- [x] **T-003** — Add the Spanish/Portuguese section markers and the native language names.
  - **Covers:** AC-003, AC-004 · **Delivers:** C-003, C-004
  - **Files:** `src/cv_writer/ingestion/data/requirement_terms.yaml`,
    `tests/unit/ingestion/test_requirement_sections.py`,
    `tests/unit/ingestion/test_term_list.py`
  - **Gate:** quick
  - **Done when:** both zone tests and all five language-name assertions pass, and `version` is
    bumped.

- [x] **T-004** — Assert no model call on the extract-to-score path.
  - **Covers:** AC-006 · **Delivers:** C-006
  - **Files:** `tests/unit/ingestion/test_no_model_calls.py`
  - **Gate:** quick
  - **Done when:** the AST check and the patched-socket run both pass.

- [ ] **T-005** — Commit the redacted real posting and assert it extracts. **BLOCKED** until
  Gustavo supplies the posting text; every other task is independent of it.
  - **Covers:** AC-005 · **Delivers:** C-005
  - **Files:** `tests/integration/ingestion/fixtures/posting_es_redacted.txt`,
    `tests/integration/ingestion/test_real_posting.py`
  - **Gate:** full
  - **Done when:** the fixture is committed and the test asserts both more than one requirement
    and named expected values.

## Struck before signature

**C-007, and its task — ship the data file with the package.** (That task was numbered T-005
before the strike; the posting-fixture task took the number when the list was renumbered.)
Proposed by the implementer citing
AC-001, then **refused by `verifier` at contract-signing on 2026-08-20**, and struck rather than
argued.

The refusal, which the implementer accepts: AC-001 says the new file must be "in the same shape
as `pt_pt_terms.yaml`", which reads as *schema* parity — `version` plus entries, pydantic
validated, already covered by C-001 — not *deployment* parity. And the contract contradicted
itself: it declared the identical packaging gap in `pt_pt_terms.yaml` out of scope in one
paragraph while mandating the fix for the new file two paragraphs later under the same AC
number. If AC-001's plain text really implied installed-package correctness, criterion 21 of
spec 001 would already be violated by `pt_pt_terms.yaml` today. One argument cannot hold in one
direction only.

Confirmed by the implementer before striking: `.venv` carries
`__editable__.cv_writer-0.1.0.pth`, `cv_writer.__file__` resolves to `src/cv_writer/`, and
`DEFAULT_TERMS_PATH.exists()` is `True` — so nothing in this feature is blocked by leaving it
out. This is new work no criterion asked for, routed back to the human as a candidate criterion
covering both files, exactly as `SKILL.md`'s Contract section requires.

## Explicitly not in this contract

- **Packaging either YAML data file into a built wheel.** `[tool.setuptools.package-data]`
  (`pyproject.toml:33-36`) lists `db/migrations/*.sql` and `web/templates/*.jinja` and no YAML,
  so neither `generation/data/pt_pt_terms.yaml` nor the new `ingestion/data/requirement_terms.yaml`
  would ship in a wheel. Both are invisible today because the venv holds an editable install
  (`__editable__.cv_writer-0.1.0.pth`) that reads `src/` in place. A real, pre-existing bug —
  reported to Gustavo, owed its own deliberate commit covering **both** files. See "Struck before
  signature" below for why it is not in this contract.
- **Moving `tests/integration/ingestion/test_requirements.py` to the unit mirror**, even though
  it tests a pure function. Relocating a working test as a side effect of another feature is
  churn. Recorded in `spec.md`'s placement note.
- **Any change to matching or scoring behaviour.** C-006 asserts scoring is untouched; it does
  not improve it.
- **A drift sensor for canonical keys that match no profile skill** — spec OQ-3, deliberately
  deferred at sign-off.
- **Graduating extraction to an LLM step** — spec 001 open question 4, explicitly out of scope
  in `spec.md`.
- **The locale-formatting bug in `generation/validator.py`** — out of scope in `spec.md`.
