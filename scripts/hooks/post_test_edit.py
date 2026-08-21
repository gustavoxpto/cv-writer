"""PostToolUse: shout if the test count just went down.

"It overwrote a test, it deleted a test, it declared everything done" is the opening scene of
the failure this harness is built against. Tests are the sensors; the cheapest way to make a red
gate go green is to remove whatever is red.

This runs after the edit, so it cannot prevent it — it makes it impossible to do quietly.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from _hook import ALLOW, BLOCK, payload, touched_path, under  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from harness_lib import python_executable, repo_root  # noqa: E402


def main() -> int:
    event = payload()
    if not under(touched_path(event), "tests"):
        return ALLOW

    result = subprocess.run(
        [python_executable(), str(repo_root() / "scripts" / "test_census.py")],
        cwd=str(repo_root()),
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        print("[harness] " + (result.stdout or "").strip(), file=sys.stderr)
        return BLOCK
    return ALLOW


if __name__ == "__main__":
    raise SystemExit(main())
