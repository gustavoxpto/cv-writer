# scripts/

**The sensors.** This is the feedback half of the harness — the part that observes what actually
happened and exits `0` or non-zero about it.

`CLAUDE.md` hard rule #4 says the agent is never the judge. These are the judges. An agent
reading its own diff and concluding it looks right is not evidence; one of these exiting 0 is.

Everything here is stdlib-only, so it runs in CI without installing the project.

## The gate

```
python scripts/gate.py quick     # ruff + unit tests
python scripts/gate.py full      # ruff + every test (unit, integration, e2e)
python scripts/gate.py build     # full + the artifact validators below
```

A task is done when the gate for its level exits 0. Not before, and not because it looks right.

## Artifact validators

Each reads one `.specs/` artifact and rejects the shapes an agent produces under pressure.

| Script | Rejects |
|---|---|
| `validate_spec.py <spec.md>` | criteria with no `SHALL`, template placeholders, duplicate IDs, sign-off claimed with an unticked box or an open blocking question |
| `validate_tasks.py <tasks.md>` | a task tracing to no criterion, a criterion no task covers, an unknown gate level, a missing "Done when" |
| `validate_contract.py <feature-dir>` | an item with no way to check it, a criterion nothing promises, an item claiming a criterion that does not exist |
| `validate_state.py <feature>` | a criterion with no `file:line`, a PASS sitting above a failed score row, a score row never run, a report still full of template text |
| `check_commit.py --message "..."` | anything that is not a Conventional Commit |

## Memory and bootstrap

| Script | Does |
|---|---|
| `bootstrap_context.py` | prints current feature, phase, open tasks, recent commits, uncommitted files. Runs automatically at `SessionStart` |
| `handoff.py --next "..."` | rewrites the `## Handoff` snapshot in `.specs/STATE.md`. Never touches `## Decisions` |
| `test_census.py [--accept]` | a ratchet on the test count. A test that vanishes is a sensor that vanished |

## hooks/

The same sensors, wired to Claude Code events so they fire without anyone remembering to run
them. See the `hooks` block in `.claude/settings.json`.

| Hook | Fires | Blocks? |
|---|---|---|
| `session_start.py` | session opens | never |
| `pre_edit_src.py` | Edit/Write under `src/` | yes — unsigned spec, or no current feature |
| `pre_commit.py` | a `git commit` command | yes — malformed message, or a red gate |
| `post_test_edit.py` | Edit/Write under `tests/` | yes — the test count dropped |
| `on_stop.py` | turn ends | never — nudges if the handoff is stale |

Every block prints its own escape hatch. `HARNESS_BYPASS=1` prefixed to a command, or a
`.specs/BYPASS` file for tool calls that carry no command. Bypassing is allowed; bypassing
silently is not — each one appends a line to `.specs/STATE.md`.

A long bypass log means a gate is miscalibrated. Fix the gate rather than routing around it.

## Other tooling

Ordinary dev helpers also live here. Once sops+age is set up (see `docs/security.md`), a
`decrypt-env` helper that runs a command with secrets injected into that process's env — never
writing plaintext to disk — belongs here too.
