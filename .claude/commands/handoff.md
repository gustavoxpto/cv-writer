---
description: Write the handoff snapshot to .specs/STATE.md so the next session knows where this one stopped
argument-hint: [what the next session should pick up]
model: haiku
---

Refresh the memory pillar before this session ends.

Run:

```
python scripts/handoff.py --next "$ARGUMENTS"
```

If no argument was given, work out the next step from the current phase and the unticked tasks
in `tasks.md`, and pass that instead of leaving it blank. "(unstated)" in a handoff is a handoff
that did not happen.

Also update `- **Phase:**` under `## Current` in `.specs/STATE.md` if it has moved on.

**Never touch `## Decisions`.** It is append-only. If a decision was made this session that is
worth keeping, append a new `AD-NNN` entry — do not edit or remove an existing one, even a
superseded one; mark it superseded and add the new entry beneath.

Then confirm to the user what was recorded.
