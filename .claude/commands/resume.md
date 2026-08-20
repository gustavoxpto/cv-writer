---
description: Rebuild session context — current feature, phase, open tasks, uncommitted work
model: haiku
---

Run `python scripts/bootstrap_context.py` and summarise it for the user in a few lines: what
feature is live, what phase it is in, what is left, and what is uncommitted.

Then read `.specs/LESSONS.md` and mention any line that bears on the work in flight.

If the output shows no current feature, or a spec that is not signed off while the phase claims
`execute`, say so plainly — that mismatch is why the next `src/` edit will be blocked.

Do not start working. This command orients; it does not act.
