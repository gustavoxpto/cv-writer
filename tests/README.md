# Tests

Mirrors `src/` 1:1. In TDD, a file here is written *before* the corresponding file in `src/`,
and it should exist before code is considered "done" — not added after the fact.

- `unit/` — one thing, in isolation, fast.
- `integration/` — multiple units together (e.g. hitting a real-ish DB/service).
- `e2e/` — the whole system, from the outside in.

Each test should trace back to a numbered acceptance criterion in a `specs/features/*.md` file
— if you can't say which criterion a test proves, it's probably testing the wrong thing.
