"""Memory: refresh the `## Handoff` snapshot in `.specs/STATE.md`.

Rewrites only that one section. `## Decisions` is append-only and is never touched here — if this
script ever starts editing it, that is a bug.

Usage:  python scripts/handoff.py
        python scripts/handoff.py --next "wire the pre-commit hook" --blockers "none"
"""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from harness_lib import current_feature, repo_root  # noqa: E402

STATE = repo_root() / ".specs" / "STATE.md"

_HANDOFF_RE = re.compile(
    r"(?P<head>^##\s+Handoff\s*$\n)(?P<body>.*?)(?=^---\s*$|^##\s|\Z)",
    re.MULTILINE | re.DOTALL,
)


def _git(*args: str) -> str:
    try:
        return subprocess.run(
            ["git", *args],
            cwd=str(repo_root()),
            capture_output=True,
            text=True,
            # git emits UTF-8; Windows would otherwise decode it with the console
            # codepage and write mojibake into an artifact meant to be read.
            encoding="utf-8",
            errors="replace",
            timeout=15,
        ).stdout.strip()
    except (OSError, subprocess.SubprocessError):
        return ""


def _arg(argv: list[str], flag: str, default: str) -> str:
    if flag in argv and argv.index(flag) + 1 < len(argv):
        return argv[argv.index(flag) + 1]
    return default


def build_body(feature: str, phase: str, next_step: str, blockers: str) -> str:
    dirty = _git("status", "--porcelain").splitlines()
    listed = ", ".join(line[3:] for line in dirty[:8]) or "clean tree"
    if len(dirty) > 8:
        listed += f", … (+{len(dirty) - 8})"
    return (
        "\nSnapshot of where work stopped. Overwrite freely — this is not a log.\n"
        "Regenerate with `python scripts/handoff.py`.\n\n"
        f"- **Feature:** `{feature or 'none'}` · phase `{phase or 'unset'}`\n"
        f"- **Branch:** `{_git('rev-parse', '--abbrev-ref', 'HEAD') or 'unknown'}`\n"
        f"- **Last commit:** {_git('log', '-1', '--oneline') or 'none'}\n"
        f"- **Next step:** {next_step}\n"
        f"- **Blockers:** {blockers}\n"
        f"- **Uncommitted:** {len(dirty)} file(s) — {listed}\n\n"
    )


def main(argv: list[str]) -> int:
    if not STATE.exists():
        print(f"handoff: no {STATE}")
        return 2
    feature, phase = current_feature()
    body = build_body(
        feature,
        phase,
        _arg(argv, "--next", "(unstated — say what the next session should pick up)"),
        _arg(argv, "--blockers", "none"),
    )
    text = STATE.read_text(encoding="utf-8")
    if not _HANDOFF_RE.search(text):
        print("handoff: no '## Handoff' section in STATE.md")
        return 2
    updated = _HANDOFF_RE.sub(lambda m: m.group("head") + body, text, count=1)
    STATE.write_text(updated, encoding="utf-8")
    print(f"handoff: updated {STATE.relative_to(repo_root())}")
    print(body.strip())
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
