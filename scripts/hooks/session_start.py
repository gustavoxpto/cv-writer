"""SessionStart: hand the session its own state instead of making it guess.

The bootstrap pillar. Without it, every new session reconstructs "what was happening here" from
the diff and the file tree, spends a large slice of its context window doing so, and still gets
it wrong. Stdout from a SessionStart hook is added to the session's context.

Never blocks. A bootstrap that can fail a session is worse than no bootstrap.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


def main() -> int:
    try:
        import bootstrap_context

        print(bootstrap_context.render())
    except Exception as error:  # noqa: BLE001 - never wedge a session over context printing
        print(f"[harness] bootstrap_context failed ({error!r}); run it by hand to see why.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
