"""Sensor: is this feature actually finished, or does it just say so?

Answers failure mode "marks a feature done without really testing it". Evidence or zero — a
criterion with no `file:line` is not covered, however obvious the coverage looks to whoever
wrote it.

Runs last, over the verifier's report. It is the check on the checker: if `validation.md` is
missing, still full of template text, or claims PASS while a score row failed, this exits
non-zero and the feature is not done.

Usage:  python scripts/validate_state.py <feature>   # e.g. 002-requirement-dictionary
        python scripts/validate_state.py .specs/features/<feature>
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from harness_lib import (  # noqa: E402
    Report,
    find_placeholders,
    parse_contract,
    parse_spec,
    parse_validation,
    repo_root,
    strip_html_comments,
)


def check(
    validation_text: str,
    spec_text: str | None = None,
    contract_text: str | None = None,
    label: str = "feature",
) -> Report:
    report = Report(name=f"validate_state({label})")
    validation = parse_validation(validation_text)

    if validation.verdict not in ("PASS", "FAIL"):
        report.error(f"Verdict is {validation.verdict or '(absent)'!r}; expected PASS or FAIL")
    elif validation.verdict == "FAIL":
        report.error(
            "verifier returned FAIL — the feature is not done; "
            "route the ranked gaps back as fix tasks"
        )

    if not validation.score_rows:
        report.error("no '## Score' table — every check needs a stated minimum, not a vibe")
    for row in validation.score_rows:
        if len(row) < 4:
            continue
        name, _score, minimum, result = row[0], row[1], row[2], row[3]
        if result.strip().upper().strip("*") in ("", "—", "-", "TBD"):
            report.error(f"score row {name!r} has no result — it was never actually run")
        elif "FAIL" in result.upper():
            report.error(
                f"score row {name!r} failed (minimum: {minimum}) but was submitted anyway"
            )

    placeholders = find_placeholders(strip_html_comments(validation_text))
    if placeholders:
        report.error(
            f"validation report still contains template placeholders {placeholders[:3]} — "
            f"a report you did not finish writing is not evidence"
        )

    if spec_text is not None:
        spec = parse_spec(spec_text)
        for cid in spec.criterion_ids:
            evidence = validation.evidence.get(cid)
            if not evidence:
                report.error(
                    f"{cid} has no file:line evidence in '## Criterion evidence' — "
                    f"evidence or zero"
                )
        if not spec.signed_off:
            report.error("the spec this validates is not signed off")

    if contract_text is not None:
        contract = parse_contract(contract_text)
        if not contract.signed:
            report.error(
                "the contract was never signed by the verifier, "
                "so nothing was agreed to validate against"
            )
        unfinished = [item.id for item in contract.items if not item.done]
        if unfinished:
            report.error(f"contract items still unticked: {unfinished}")

    return report


def _resolve(argument: str) -> Path:
    candidate = Path(argument)
    if candidate.is_dir():
        return candidate
    return repo_root() / ".specs" / "features" / argument


def main(argv: list[str]) -> int:
    if len(argv) != 2:
        print(__doc__)
        return 2
    directory = _resolve(argv[1])
    validation_path = directory / "validation.md"
    if not validation_path.exists():
        print(f"validate_state: FAIL — no validation report at {validation_path}")
        print("  The verifier has not run. A feature nobody independently checked is not finished.")
        return 1

    def read(name: str) -> str | None:
        path = directory / name
        return path.read_text(encoding="utf-8") if path.exists() else None

    return check(
        validation_path.read_text(encoding="utf-8"),
        spec_text=read("spec.md"),
        contract_text=read("contract.md"),
        label=directory.name,
    ).emit()


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
