# 2026-08-21 — Spec 002 through the full six-phase loop, first time

## Goal

Run `002-requirement-dictionary-expansion` end to end through the harness built the day before —
Specify, Contract, Execute, Validate — and find out whether the loop actually catches things, or
whether it is ceremony that produces the same code more slowly.

Starting position was awkward on purpose: an untested ad hoc widening of `SKILL_TERMS` was sitting
uncommitted from the 2026-08-19 operational-readiness run, needed by real applications, covered by
no test.

## Tried

**Committing the stopgap first, deliberately, rather than reverting it or hiding it.** `387d937`
went in with a body stating in its first line that the behaviour is untested. The alternative —
carrying it as an uncommitted working-tree change — is strictly worse: same untested behaviour,
no record of why it exists. Spec 002's Appendix A then pinned the exact surface so the debt had a
shape.

**Proposing scope creep and getting caught.** The first contract contained C-007: add
`ingestion/data/*.yaml` to setuptools `package-data`, justified under AC-001. The verifier refused
to sign, pointing at the contract's own text — it declared the identical packaging gap in
`pt_pt_terms.yaml` out of scope in one paragraph and mandated the same fix for the new file two
paragraphs later, under the same AC number. Struck, and the strike recorded in the file.

**Writing two tests that could not fail.** Both `Requisitos:` zone tests passed before the marker
existed, because "required" is the extractor's default zone. Rewritten so a *preferred* heading
sits above the required one — which reads oddly for a job advert and is the only arrangement where
the marker has to be recognised.

**Claiming a guarantee that had no sensor.** `3acb395`'s message said the fixture redactions were
"assert-checked as applied and then assert-checked as absent". True — inside a one-off generation
script in a scratch directory that was never committed. The repo was guarding nothing. Iteration 2
of validation caught it.

## Decided

- **OQ-1: hand-maintain canonical keys in the YAML**, do not derive them from `profile.yaml`.
  Deriving removes duplication but makes the extractor structurally unable to recognise a
  requirement the profile does not already claim — and a requirement Gustavo cannot meet is a gap
  the match report should *show*, not a term to drop at extraction. Accepted cost recorded as OQ-3.
- **The `==` snapshot survives, split rather than relaxed.** T-003 extends languages and markers,
  which broke the frozen equality. Rather than downgrade to a subset check, it became a permanent
  no-loss assertion plus an equality against a written-out expected value, so future additions
  still surface as deliberate edits.
- **AC-005a's provenance rule became a sensor.** The verifier signed the contract with a
  reservation that provenance was inspection-only. A fixture assembled from the term file would
  consist largely of phrases that file contains, so the test asserts >80% of the fixture's words
  appear nowhere in the vocabulary. The verifier then checked the threshold was meaningful by
  building a reconstructed fixture and measuring it: 0.02 against the real fixture's 0.87.
- **The German bug was left alone.** The real posting lists `alemán` under `Se valorará`, but
  languages are not zoned — only skills are — so it is reported as required. Real defect, no
  criterion covers it, fixing it here would be the same scope creep C-007 was struck for. It gets
  its own spec.

## Learned

**The loop's value is concentrated in two places, and neither is the part that felt like work.**

Writing the spec and the tasks felt like the substance. It was not. Every real catch came from the
two places where a *different agent with a different mission* looked at the work: the contract
refusal before any code existed, and the three validation iterations after. Feed-forward stopped
nothing on its own — I wrote the scope creep *while holding the document that forbids it*.

**A green gate is not evidence about untested code.** `387d937` passed the gate with 259 tests. It
had to: those tests said nothing about the new terms. The gate is a regression sensor, and it was
never watching the thing that mattered. This is the concrete version of hard rule #4 that was
previously an abstraction.

**Mutation testing found what reading twice did not.** Three surviving mutants across three
iterations, each in code that looked obviously correct. The most instructive was iteration 2's:
the fixture's provenance header was never tested as stripped, and feeding the raw file through
made the provenance sensor read *better* (0.870 → 0.895) rather than warning. A sensor that
improves when fed the wrong input is measuring something other than what it claims to.

**Still fuzzy:** where the line sits between "a defect the fixture exposed, fix it now" and "a new
criterion". The German zoning bug is clearly the latter. The packaging gap felt like the former
until the verifier showed the argument was inconsistent. The test that seems to settle it: would
fixing this require a claim the signed spec does not make? If yes, it is a new criterion.

## Links

- Spec: `.specs/features/002-requirement-dictionary-expansion/spec.md`
- Contract, including the struck C-007: `.specs/features/002-requirement-dictionary-expansion/contract.md`
- Validation, three iterations: `.specs/features/002-requirement-dictionary-expansion/validation.md`
- Lessons added: L-006 (worktree mutation testing against an editable install), L-007 (tests that
  the default already satisfies)
