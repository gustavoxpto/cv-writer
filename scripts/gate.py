"""The gate. The only thing in this repository allowed to declare code correct.

CLAUDE.md hard rule #4: the agent is never the judge. An agent reading its own diff and
concluding it looks right is not evidence — this exiting 0 is. If you did not run this, the task
is not done, and you may not say it is.

Levels:
    quick   ruff + unit tests                       — a task touching unit-tested code
    full    ruff + every test (unit/integration/e2e) — a task touching integration or e2e behaviour
    build   full + the harness artifact validators   — last task in a phase, or config-only work

Usage:  python scripts/gate.py quick|full|build
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from harness_lib import python_executable, repo_root, run  # noqa: E402

LEVELS = ("quick", "full", "build")


def _lint(python: str) -> int:
    return run([python, "-m", "ruff", "check", "src", "tests", "scripts"])


def _tests(python: str, paths: list[str]) -> int:
    return run([python, "-m", "pytest", *paths, "-q"])


def _validate_artifacts(python: str) -> int:
    """Run the artifact sensors over every feature that has reached a given phase.

    Absence of a file means the phase was skipped, which is legitimate (see the auto-sizing
    table in the spec-driven skill) — only files that exist get checked.
    """
    features = sorted((repo_root() / ".specs" / "features").glob("*/"))
    worst = 0
    for feature in features:
        for artifact, script in (
            ("spec.md", "validate_spec.py"),
            ("tasks.md", "validate_tasks.py"),
            ("contract.md", "validate_contract.py"),
        ):
            path = feature / artifact
            if path.exists():
                target = str(feature) if script == "validate_contract.py" else str(path)
                worst = max(worst, run([python, str(repo_root() / "scripts" / script), target]))
    return worst


def gate(level: str) -> int:
    python = python_executable()
    if level == "quick":
        return max(_lint(python), _tests(python, ["tests/unit"]))
    if level == "full":
        return max(_lint(python), _tests(python, ["tests"]))
    if level == "build":
        return max(_lint(python), _tests(python, ["tests"]), _validate_artifacts(python))
    raise ValueError(level)


def main(argv: list[str]) -> int:
    level = argv[1] if len(argv) > 1 else ""
    if level not in LEVELS:
        print(__doc__)
        return 2
    code = gate(level)
    print()
    print(f"gate({level}): {'PASS' if code == 0 else 'FAIL'}")
    if code != 0:
        print("  Do not commit, and do not report this task as done. Fix it or escalate.")
    return code


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
