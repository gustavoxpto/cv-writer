# Contract: <NNN-slug>

- **Spec:** `.specs/features/<NNN-slug>/spec.md`
- **Implementer:** `implementer`
- **Verifier:** `verifier`
- **Date:** <YYYY-MM-DD>

<!--
The contract is written by the IMPLEMENTER before any code exists, and signed by the VERIFIER
after checking it against the spec. It is the agreed checklist both sides work from.

Why it exists — two failures it prevents:
  1. Work slipping through. The verifier walks this list item by item, so nothing is silently
     skipped and nothing is silently declared done.
  2. Verifier drift. Without an agreed list, a verifier starts proposing unrelated improvements
     and the implementer chases them forever. The contract bounds what "done" means.

Validate with: python scripts/validate_contract.py .specs/features/<NNN-slug>
-->

## Signature

- [ ] **Verifier has checked this list against `spec.md`** and confirms it covers every
      acceptance criterion, adds nothing outside the spec, and that each **Check** below is
      something a sensor or an inspection can actually decide.

*(Execute does not start until this box is checked. Anything the verifier wants that is not on
this list must go back into the spec first — it does not get added at validation time.)*

## What will be built

Each item is one observable outcome. Not a task, not a file — an outcome someone else can check.

- [ ] **C-001** — <observable outcome>
  - **Verifies:** AC-001
  - **Check:** <exactly how the verifier will confirm it — the command to run, the assertion to
    look for, the file:line to find>

- [ ] **C-002** — <observable outcome>
  - **Verifies:** AC-002, AC-003
  - **Check:** <…>

## Explicitly not in this contract

Things the implementer will *not* do, so the verifier does not raise them as gaps. If one of
these turns out to matter, it becomes a new criterion in the spec, not a surprise at validation.

- <…>
