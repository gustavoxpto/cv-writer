"""Sensor: is this commit message a valid Conventional Commit?

One task, one commit, one readable message — that is what makes `git bisect` and `git revert`
work, which is what makes hard rule #1 ("never delete, prefer revert") affordable.

Usage:  python scripts/check_commit.py --message "feat(002): add pt-PT skill terms"
        python scripts/check_commit.py --file .git/COMMIT_EDITMSG
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from harness_lib import Report  # noqa: E402

TYPES = ("feat", "fix", "refactor", "docs", "test", "style", "perf", "build", "ci", "chore")

HEADER_RE = re.compile(
    rf"^(?P<type>{'|'.join(TYPES)})"
    r"(?:\((?P<scope>[a-z0-9][a-z0-9._/-]*)\))?"
    r"(?P<breaking>!)?"
    r": (?P<description>.+)$"
)

MAX_HEADER = 72


def check(message: str) -> Report:
    report = Report(name="check_commit")
    lines = message.strip().splitlines()
    if not lines:
        report.error("empty commit message")
        return report

    header = lines[0]
    match = HEADER_RE.match(header)
    if not match:
        report.error(
            f"header does not match '<type>(<scope>): <description>': {header!r}\n"
            f"        valid types: {', '.join(TYPES)}"
        )
        return report

    description = match.group("description")
    if len(header) > MAX_HEADER:
        report.error(f"header is {len(header)} chars; keep it to {MAX_HEADER}")
    if description[0].isupper():
        report.error(f"description should start lowercase: {description!r}")
    if description.endswith("."):
        report.error("description should not end with a period")
    if description.split()[0].endswith(("ed", "ing")):
        report.warn(
            f"description looks past-tense or gerund ({description.split()[0]!r}); "
            f"use the imperative — it should complete 'If applied, this commit will …'"
        )

    if len(lines) > 1 and lines[1].strip():
        report.error("leave a blank line between the header and the body")

    if match.group("breaking") and "BREAKING CHANGE:" not in message:
        report.error("header is marked '!' but there is no 'BREAKING CHANGE:' footer justifying it")

    return report


def main(argv: list[str]) -> int:
    if len(argv) == 3 and argv[1] == "--message":
        message = argv[2]
    elif len(argv) == 3 and argv[1] == "--file":
        message = Path(argv[2]).read_text(encoding="utf-8")
    else:
        print(__doc__)
        return 2
    return check(message).emit()


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
