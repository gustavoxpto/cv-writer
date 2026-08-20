---
description: Contract phase — implementer writes what it will build, verifier signs it against the spec, before any code
argument-hint: <NNN-slug>
model: sonnet
---

Run the **Contract** phase for: **$ARGUMENTS**

This is the agreement between the two missions, made before any code exists. It prevents two
distinct failures: work slipping through unnoticed, and a verifier drifting into unrelated
suggestions that the implementer then chases forever.

**Step 1 — draft.** Dispatch the `implementer` subagent with `spec.md`, `tasks.md` and
`.specs/templates/contract.md`. It writes `.specs/features/<slug>/contract.md`: each item an
**observable outcome** (not a file, not a task), with the exact **Check** the verifier will run.
It does not write any code in this step.

**Step 2 — sign.** Dispatch the `verifier` subagent, fresh, with `spec.md` and the drafted
contract. It confirms:

- every criterion in the spec is promised by at least one contract item
- nothing is promised that the spec did not ask for
- every **Check** is something a sensor or an inspection can actually decide

It ticks the signature box only if all three hold. If not, it returns what is wrong and step 1
repeats. Anything the verifier wants that the spec does not contain goes back to `/spec` as a new
criterion — it does not get bolted onto the contract, and it does not get raised later at
validation.

**Step 3.** Run `python scripts/validate_contract.py .specs/features/<slug>` — it must exit 0 and
report the contract as signed. Set `- **Phase:** contract` in `.specs/STATE.md`.

Next: `/implement <slug>`.
