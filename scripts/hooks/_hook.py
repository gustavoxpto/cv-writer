"""Shared plumbing for Claude Code hooks.

Hooks are the part of the harness that actually bites. A warning an agent can ignore is
feed-forward wearing a sensor's clothes — so these exit 2, which Claude Code treats as a block
and feeds back as an instruction to fix.

Every block prints its own escape hatch. Bypassing is allowed; bypassing silently is not.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from harness_lib import bypass_requested, log_bypass  # noqa: E402

ALLOW = 0
BLOCK = 2


def payload() -> dict:
    """The hook event JSON on stdin. Never raises — a broken hook must not wedge a session."""
    try:
        return json.loads(sys.stdin.read() or "{}")
    except (json.JSONDecodeError, OSError):
        return {}


def tool_input(event: dict) -> dict:
    value = event.get("tool_input")
    return value if isinstance(value, dict) else {}


def block(
    title: str,
    reason: str,
    fix: list[str],
    bypass_hint: str,
    what: str,
    command: str = "",
) -> int:
    """Refuse the action — unless a bypass was requested, in which case allow it and log it."""
    if bypass_requested(command):
        log_bypass(what)
        print(f"[harness] BYPASSED: {title} — logged to .specs/STATE.md", file=sys.stderr)
        return ALLOW

    lines = [f"[harness] BLOCKED: {title}", "", reason, ""]
    lines += [f"  {line}" for line in fix]
    lines += ["", "  If this gate is wrong for what you are doing, override it deliberately:"]
    lines += [f"  {bypass_hint}"]
    print("\n".join(lines), file=sys.stderr)
    return BLOCK


def touched_path(event: dict) -> Path | None:
    raw = tool_input(event).get("file_path")
    return Path(str(raw)) if raw else None


def under(path: Path | None, *parts: str) -> bool:
    """Is *path* inside one of the given top-level directories, on either slash convention?"""
    if path is None:
        return False
    text = str(path).replace("\\", "/")
    return any(f"/{part}/" in f"/{text}" for part in parts)
