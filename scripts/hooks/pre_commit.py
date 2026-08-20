"""PreToolUse: refuse a commit with a malformed message or a red gate.

Two checks, in the order that fails cheapest first:

  1. Conventional Commits — one task, one commit, one readable message. That is what keeps
     `git revert` and `git bisect` usable, which is what makes "never delete, prefer revert"
     (hard rule #1) an affordable rule rather than a slogan.
  2. `gate.py quick` — hard rule #4. Committing on a red gate is how an agent declares victory
     without evidence. The runner decides, not the agent.

Merge commits, `--amend`, and `--no-verify` are left alone; so is anything that is not a commit.
"""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from _hook import ALLOW, block, payload, tool_input  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import check_commit  # noqa: E402
from harness_lib import python_executable, repo_root  # noqa: E402

_MESSAGE_RE = re.compile(r"""-m\s+(?P<quote>["'])(?P<message>.*?)(?<!\\)(?P=quote)""", re.DOTALL)
# Global options may carry their own argument ("git -C <path> commit"), so allow an optional
# value token after each flag. Without that, `git -C . commit` walks straight past this guard.
_IS_COMMIT_RE = re.compile(r"\bgit\s+(?:-{1,2}\S+(?:\s+\S+)?\s+)*commit\b")


def extract_message(command: str) -> str | None:
    matches = _MESSAGE_RE.findall(command)
    return "\n\n".join(m[1] for m in matches) if matches else None


def main() -> int:
    event = payload()
    command = str(tool_input(event).get("command", ""))
    if not _IS_COMMIT_RE.search(command):
        return ALLOW
    if "--amend" in command or "--no-edit" in command:
        return ALLOW

    message = extract_message(command)
    if message is not None:
        report = check_commit.check(message)
        if not report.ok:
            return block(
                title="commit message is not a Conventional Commit",
                reason="\n".join(f"  - {problem}" for problem in report.errors),
                fix=[
                    "Format:  <type>(<scope>): <description>",
                    f"Types:   {', '.join(check_commit.TYPES)}",
                    "The description completes 'If applied, this commit will ___':",
                    "imperative, lowercase, no period.",
                    'Check it:  python scripts/check_commit.py --message "..."',
                ],
                bypass_hint="prefix the command with  HARNESS_BYPASS=1  (it will be logged).",
                what="commit with a malformed message",
                command=command,
            )

    result = subprocess.run(
        [python_executable(), str(repo_root() / "scripts" / "gate.py"), "quick"],
        cwd=str(repo_root()),
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        tail = "\n".join((result.stdout or "").strip().splitlines()[-25:])
        return block(
            title="the gate is red",
            reason=(
                "`python scripts/gate.py quick` did not exit 0, so this commit would record code "
                "that lint or the unit tests reject. Hard rule #4: the runner decides, not you.\n\n"
                + tail
            ),
            fix=[
                "Fix the failures, then re-run:  python scripts/gate.py quick",
                "Do not weaken an assertion, skip a test, or delete a test to get here.",
            ],
            bypass_hint="prefix the command with  HARNESS_BYPASS=1  (it will be logged).",
            what="commit on a red gate",
            command=command,
        )

    return ALLOW


if __name__ == "__main__":
    raise SystemExit(main())
