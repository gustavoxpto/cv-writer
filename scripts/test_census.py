"""Sensor: did the test count just go down?

Straight from the failure this harness exists to stop: "it overwrote a test, it deleted a test,
it declared everything done." Tests are the sensors; an agent under pressure to make a gate pass
can make the gate pass by removing what fails. This notices.

It is a ratchet, not a rule — a deliberate reduction is fine, it just has to be deliberate.
Re-baseline with `--accept` once a human has agreed the drop is correct.

Usage:  python scripts/test_census.py            # compare against the baseline
        python scripts/test_census.py --accept   # record the current count as the new baseline
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from harness_lib import repo_root  # noqa: E402

BASELINE = repo_root() / ".specs" / "test-census.json"
TEST_DEF = re.compile(r"^\s*(?:async\s+)?def\s+test_\w+", re.MULTILINE)


def count_tests(tests_dir: Path) -> tuple[int, int]:
    """(number of test functions, number of test files)."""
    total = 0
    files = sorted(tests_dir.rglob("test_*.py"))
    for path in files:
        total += len(TEST_DEF.findall(path.read_text(encoding="utf-8", errors="replace")))
    return total, len(files)


def read_baseline() -> int | None:
    if not BASELINE.exists():
        return None
    try:
        return int(json.loads(BASELINE.read_text(encoding="utf-8"))["tests"])
    except (ValueError, KeyError, TypeError):
        return None


def write_baseline(tests: int, files: int) -> None:
    BASELINE.write_text(
        json.dumps({"tests": tests, "files": files}, indent=2) + "\n", encoding="utf-8"
    )


def main(argv: list[str]) -> int:
    tests, files = count_tests(repo_root() / "tests")
    if "--accept" in argv:
        write_baseline(tests, files)
        print(f"test_census: baseline set to {tests} tests across {files} files")
        return 0

    baseline = read_baseline()
    if baseline is None:
        write_baseline(tests, files)
        print(f"test_census: no baseline yet — recorded {tests} tests across {files} files")
        return 0

    if tests < baseline:
        print(f"test_census: TEST COUNT DROPPED — {baseline} -> {tests} ({baseline - tests} fewer)")
        print("  A test that disappeared is a sensor that disappeared. Two possibilities:")
        print("    1. This was accidental, or was done to make a gate pass. Restore it.")
        print("    2. It was deliberate and a human agreed. Then run:")
        print("         python scripts/test_census.py --accept")
        return 1

    if tests > baseline:
        write_baseline(tests, files)
        print(f"test_census: {baseline} -> {tests} tests (baseline raised)")
        return 0

    print(f"test_census: {tests} tests across {files} files (unchanged)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
