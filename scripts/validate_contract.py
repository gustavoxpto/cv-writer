"""Sensor: has the implementer and the verifier agreed on what "done" means, before any code?

This is the mechanic the rest of the harness leans on. Two failures it prevents:

  1. Work slipping through — the verifier walks this exact list item by item at validation time,
     so nothing is silently skipped and nothing is silently declared finished.
  2. Verifier drift — without an agreed list, a verifier starts raising unrelated improvements and
     the implementer chases them forever. The contract is the boundary of the conversation.

Usage:  python scripts/validate_contract.py .specs/features/<feature>
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
)


def check(contract_text: str, spec_text: str | None = None, label: str = "contract") -> Report:
    report = Report(name=f"validate_contract({label})")
    contract = parse_contract(contract_text)

    if not contract.items:
        report.error("no contract items found — expected items like '- [ ] **C-001** — …'")

    seen: set[str] = set()
    for item in contract.items:
        if item.id in seen:
            report.error(f"{item.id} is defined more than once")
        seen.add(item.id)

        if not item.verifies:
            report.error(
                f"{item.id} has no '**Verifies:**' criterion — it is not traceable to the spec"
            )
        if not item.check:
            report.error(
                f"{item.id} has no '**Check:**' — the verifier needs to know exactly how it will "
                f"confirm this, decided now rather than improvised later"
            )
        elif find_placeholders(item.check):
            report.error(f"{item.id} '**Check:**' still contains template placeholders")

    if spec_text is not None:
        spec = parse_spec(spec_text)
        promised = {cid for item in contract.items for cid in item.verifies}
        for cid in spec.criterion_ids:
            if cid not in promised:
                report.error(f"{cid} is in the spec but no contract item promises to deliver it")
        for cid in sorted(promised - set(spec.criterion_ids)):
            report.error(f"a contract item claims {cid}, which does not exist in the spec")

    if not contract.signed:
        # Not an error: an unsigned contract is the normal state while it is being drafted.
        # It becomes an error at the point Execute starts — see scripts/hooks/pre_edit_src.py.
        report.warn("contract is not signed by the verifier yet — Execute must not start")

    return report


def main(argv: list[str]) -> int:
    if len(argv) != 2:
        print(__doc__)
        return 2
    target = Path(argv[1])
    contract_path = target if target.is_file() else target / "contract.md"
    if not contract_path.exists():
        print(f"validate_contract: no such file: {contract_path}")
        return 2
    spec_path = contract_path.parent / "spec.md"
    spec_text = spec_path.read_text(encoding="utf-8") if spec_path.exists() else None
    return check(
        contract_path.read_text(encoding="utf-8"),
        spec_text=spec_text,
        label=contract_path.parent.name,
    ).emit()


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
