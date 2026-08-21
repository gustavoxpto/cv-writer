"""Sensor: is this spec structurally fit to write failing tests from?

Answers failure mode "premature victory" at the source — an agent cannot declare a feature done
against a criterion that was never precise enough to test.

Usage:  python scripts/validate_spec.py .specs/features/<feature>/spec.md
Exit 0 = pass. Non-zero = fix the spec before going further.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from harness_lib import (  # noqa: E402
    Report,
    find_placeholders,
    parse_spec,
    section_body,
    strip_html_comments,
)

REQUIRED_SECTIONS = ("Why", "Acceptance criteria", "Out of scope", "Open questions", "Sign-off")
VALID_STATUSES = ("draft", "signed-off", "implemented")
VALID_SIZES = ("small", "medium", "large", "complex")


def check(text: str, label: str = "spec") -> Report:
    report = Report(name=f"validate_spec({label})")
    spec = parse_spec(text)
    body = strip_html_comments(text)

    for name in REQUIRED_SECTIONS:
        if name not in spec.section_names:
            report.error(f"missing required section '## {name}'")

    if spec.status not in VALID_STATUSES:
        report.error(f"Status is {spec.status or '(absent)'!r}; expected one of {VALID_STATUSES}")
    if spec.size not in VALID_SIZES:
        report.error(f"Size is {spec.size or '(absent)'!r}; expected one of {VALID_SIZES}")

    if not spec.criteria:
        report.error("no acceptance criteria found — expected items like '- **AC-001** — …SHALL…'")

    seen: set[str] = set()
    for criterion in spec.criteria:
        if criterion.id in seen:
            report.error(
                f"{criterion.id} is defined more than once; IDs must be unique and stable"
            )
        seen.add(criterion.id)

        if "SHALL" not in criterion.text:
            report.error(
                f"{criterion.id} does not contain 'SHALL' — EARS notation is required so the "
                f"criterion has exactly one reading: {criterion.text[:70]!r}"
            )
        placeholders = find_placeholders(criterion.text)
        if placeholders:
            report.error(f"{criterion.id} still contains template placeholders: {placeholders[:3]}")

    why = section_body(body, "Why")
    if len(why.strip()) < 40:
        report.error("'## Why' is empty or too thin to justify building anything")
    elif find_placeholders(why, prose=True):
        report.error("'## Why' still contains template placeholders")

    if spec.status == "signed-off":
        if not spec.signoff_boxes:
            report.error("Status is 'signed-off' but there are no sign-off checkboxes")
        elif not all(checked for checked, _ in spec.signoff_boxes):
            unchecked = [label for checked, label in spec.signoff_boxes if not checked]
            report.error(
                f"Status is 'signed-off' but {len(unchecked)} box(es) are unticked: {unchecked}"
            )
        for question in spec.blocking_open_questions:
            report.error(
                f"blocking open question unresolved but the spec claims sign-off: {question[:80]!r}"
            )
    elif spec.blocking_open_questions:
        report.warn(
            f"{len(spec.blocking_open_questions)} blocking open question(s) still open — "
            f"cannot sign off yet"
        )

    return report


def main(argv: list[str]) -> int:
    if len(argv) != 2:
        print(__doc__)
        return 2
    path = Path(argv[1])
    if not path.exists():
        print(f"validate_spec: no such file: {path}")
        return 2
    return check(path.read_text(encoding="utf-8"), label=path.parent.name or path.name).emit()


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
