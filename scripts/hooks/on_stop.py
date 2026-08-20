"""Stop: nudge if the session is ending with state that the next session cannot recover.

Non-blocking by design. A Stop hook that refuses to let a session end can trap it in a loop, and
a memory nudge is not worth that risk — so this only prints.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from harness_lib import repo_root  # noqa: E402


def main() -> int:
    try:
        dirty = subprocess.run(
            ["git", "status", "--porcelain"],
            cwd=str(repo_root()),
            capture_output=True,
            text=True,
            timeout=15,
        ).stdout
    except (OSError, subprocess.SubprocessError):
        return 0

    changed = [line[3:].strip() for line in dirty.splitlines() if line.strip()]
    if not changed:
        return 0
    if any(name.startswith(".specs/STATE.md") for name in changed):
        return 0

    print(
        f"[harness] {len(changed)} uncommitted file(s) and `.specs/STATE.md` was not touched. "
        f"The next session will not know where this one stopped. "
        f'Run:  python scripts/handoff.py --next "<what to pick up>"'
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
