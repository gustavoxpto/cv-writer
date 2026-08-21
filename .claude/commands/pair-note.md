---
description: Write the pairing session note and distil any generalisable rule into LESSONS.md
argument-hint: [topic]
model: haiku
---

Dispatch the `pair-scribe` subagent to write `pairing/sessions/YYYY-MM-DD-<topic>.md` for this
session, following `pairing/sessions/README.md`: **Goal**, **Tried**, **Decided**, **Learned**,
and optionally **Next**.

Give it what actually happened this session, including the approaches that were tried and backed
out of. **Tried** is the section that justifies the folder existing — a note recording only what
worked has thrown away the useful half.

If something generalises, it appends one `L-NNN` line to `.specs/LESSONS.md` with the failure
that produced it. Most sessions produce none; do not invent one to fill space.

Then run `python scripts/handoff.py`.

Topic: **$ARGUMENTS**
