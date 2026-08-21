"""Bootstrap: rebuild session context without reading the whole repository.

A fresh agent session starts with no memory of what came before. Left to itself it reconstructs
that from the diff and the file tree, and burns a large slice of its context window doing it —
badly. This prints the answer instead: what feature is live, what phase it is in, what is left
to do, and what is uncommitted.

Runs automatically via the SessionStart hook. Run it by hand any time you are lost.

Usage:  python scripts/bootstrap_context.py
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from harness_lib import (  # noqa: E402
    current_feature,
    feature_dir,
    parse_spec,
    parse_tasks,
    repo_root,
    section_body,
    strip_html_comments,
)

MAX_OPEN_TASKS = 6


def _git(*args: str) -> str:
    try:
        return subprocess.run(
            ["git", *args],
            cwd=str(repo_root()),
            capture_output=True,
            text=True,
            # git emits UTF-8; Windows would otherwise decode it with the console codepage and
            # print mojibake into the very context this exists to make legible.
            encoding="utf-8",
            errors="replace",
            timeout=15,
        ).stdout.strip()
    except (OSError, subprocess.SubprocessError):
        return ""


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8") if path.exists() else ""


def render() -> str:
    out: list[str] = ["## Harness state (scripts/bootstrap_context.py)", ""]

    feature, phase = current_feature()
    branch = _git("rev-parse", "--abbrev-ref", "HEAD") or "(unknown)"
    out.append(f"- **Branch:** `{branch}`")

    if not feature:
        out.append("- **Feature:** none set in `.specs/STATE.md`. Start with `/spec <slug>`.")
    else:
        directory = feature_dir(feature)
        spec_text = _read(directory / "spec.md")
        spec = parse_spec(spec_text) if spec_text else None
        status = spec.status if spec else "no spec.md"
        signed = " (signed off)" if spec and spec.signed_off else " — **NOT signed off**"
        out.append(f"- **Feature:** `{feature}`")
        out.append(f"- **Phase:** {phase or 'unset'} | spec status: {status}{signed}")

        artifacts = ("design.md", "tasks.md", "contract.md", "validation.md")
        present = [name for name in artifacts if (directory / name).exists()]
        out.append(f"- **Artifacts:** {', '.join(present) if present else 'spec only'}")

        tasks_text = _read(directory / "tasks.md")
        if tasks_text:
            tasks = parse_tasks(tasks_text)
            open_tasks = [t for t in tasks.tasks if not t.done]
            done = len(tasks.tasks) - len(open_tasks)
            out.append(f"- **Tasks:** {done}/{len(tasks.tasks)} complete")
            for task in open_tasks[:MAX_OPEN_TASKS]:
                covers = ", ".join(task.covers) or "?"
                out.append(
                    f"    - [ ] {task.id} — {task.title} (covers {covers}, gate {task.gate or '?'})"
                )
            if len(open_tasks) > MAX_OPEN_TASKS:
                out.append(f"    - … and {len(open_tasks) - MAX_OPEN_TASKS} more")

    state_text = strip_html_comments(_read(repo_root() / ".specs" / "STATE.md"))
    handoff = section_body(state_text, "Handoff").strip()
    if handoff:
        out += ["", "**Handoff:**", ""]
        out += [line for line in handoff.splitlines() if line.strip().startswith("- ")]

    dirty = _git("status", "--porcelain")
    out += ["", f"**Uncommitted:** {len(dirty.splitlines()) if dirty else 0} file(s)"]
    for line in dirty.splitlines()[:10]:
        out.append(f"    {line}")

    recent = _git("log", "-5", "--oneline")
    if recent:
        out += ["", "**Recent commits:**"]
        out += [f"    {line}" for line in recent.splitlines()]

    out += [
        "",
        "Read `.specs/LESSONS.md` before proposing anything.",
        "The gate is `python scripts/gate.py <level>`.",
    ]
    return "\n".join(out)


def main() -> int:
    print(render())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
