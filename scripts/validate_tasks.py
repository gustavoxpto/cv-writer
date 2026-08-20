"""Sensor: is this task breakdown atomic, traceable, and gated?

Answers failure mode "one-shot hero" — work that was never decomposed is work that blows the
context window halfway through and leaves a minefield behind.

Every task must trace to at least one acceptance criterion. A task with no criterion is either
scope creep or a missing criterion; both are bugs, and neither should reach Execute.

Usage:  python scripts/validate_tasks.py .specs/features/<feature>/tasks.md
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from harness_lib import (  # noqa: E402
    VALID_GATES,
    Report,
    find_placeholders,
    parse_spec,
    parse_tasks,
)


def check(tasks_text: str, spec_text: str | None = None, label: str = "tasks") -> Report:
    report = Report(name=f"validate_tasks({label})")
    tasks = parse_tasks(tasks_text)

    if not tasks.tasks:
        report.error("no tasks found — expected items like '- [ ] **T-001** — …'")

    seen: set[str] = set()
    for task in tasks.tasks:
        if task.id in seen:
            report.error(f"{task.id} is defined more than once")
        seen.add(task.id)

        if not task.covers:
            report.error(
                f"{task.id} has no '**Covers:**' criterion — a task that traces to no criterion "
                f"is scope creep or a missing criterion, not work to do"
            )
        if not task.files:
            report.error(
                f"{task.id} has no '**Files:**' — an implementer must know its blast radius"
            )
        if task.gate not in VALID_GATES:
            report.error(
                f"{task.id} has Gate {task.gate or '(absent)'!r}; expected one of {VALID_GATES}"
            )
        if not task.done_when:
            report.error(f"{task.id} has no '**Done when:**' — nothing for a sensor to confirm")
        elif find_placeholders(task.done_when):
            report.error(f"{task.id} '**Done when:**' still contains template placeholders")

    if spec_text is not None:
        spec = parse_spec(spec_text)
        covered = {cid for task in tasks.tasks for cid in task.covers}
        for cid in spec.criterion_ids:
            if cid not in covered:
                report.error(f"{cid} is in the spec but no task covers it")
            if cid not in tasks.coverage_matrix_ids:
                report.warn(f"{cid} is missing from the '## Coverage matrix' table")
        unknown = covered - set(spec.criterion_ids)
        for cid in sorted(unknown):
            report.error(f"a task claims to cover {cid}, which does not exist in the spec")

    return report


def main(argv: list[str]) -> int:
    if len(argv) != 2:
        print(__doc__)
        return 2
    path = Path(argv[1])
    if not path.exists():
        print(f"validate_tasks: no such file: {path}")
        return 2
    spec_path = path.parent / "spec.md"
    spec_text = spec_path.read_text(encoding="utf-8") if spec_path.exists() else None
    return check(
        path.read_text(encoding="utf-8"), spec_text=spec_text, label=path.parent.name or path.name
    ).emit()


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
