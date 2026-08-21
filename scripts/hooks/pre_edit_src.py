"""PreToolUse: refuse to write application code that no signed-off spec asked for.

CLAUDE.md hard rule #3 — spec before code — was prose until now, which meant it held exactly as
long as an agent remembered it. This makes it structural: `src/**` is unwritable until
`.specs/STATE.md` names a feature whose `spec.md` is signed off by a human.

Deliberately narrow. It guards `src/` only. Tests, specs, docs, scripts and the harness itself
stay freely editable — you must be able to write the failing test before the code exists.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from _hook import ALLOW, block, payload, touched_path, under  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from harness_lib import current_feature, feature_dir, parse_spec  # noqa: E402


def main() -> int:
    event = payload()
    path = touched_path(event)
    if not under(path, "src"):
        return ALLOW

    feature, _phase = current_feature()
    if not feature:
        return block(
            title="no feature is in play",
            reason=(
                f"You are about to change {path}, but `.specs/STATE.md` does not name a current "
                f"feature. Application code that no spec asked for is the slop this harness exists "
                f"to stop."
            ),
            fix=[
                "Write the spec first:  /spec <slug>",
                "Then set `- **Feature:** <slug>` under `## Current` in .specs/STATE.md.",
            ],
            bypass_hint="create a file `.specs/BYPASS` saying why (it will be logged), then retry.",
            what=f"edit to {path} with no current feature",
        )

    spec_path = feature_dir(feature) / "spec.md"
    if not spec_path.exists():
        return block(
            title=f"feature '{feature}' has no spec",
            reason=(
                f"`.specs/STATE.md` says the current feature is '{feature}', "
                f"but {spec_path} does not exist."
            ),
            fix=[
                f"Run:  /spec {feature}",
                "Or correct the feature name under `## Current` in .specs/STATE.md.",
            ],
            bypass_hint="create a file `.specs/BYPASS` saying why (it will be logged), then retry.",
            what=f"edit to {path} with no spec.md for {feature}",
        )

    spec = parse_spec(spec_path.read_text(encoding="utf-8"))
    if not spec.signed_off:
        unticked = [label for checked, label in spec.signoff_boxes if not checked]
        return block(
            title=f"spec for '{feature}' is not signed off",
            reason=(
                f"Status is '{spec.status or 'unset'}' and {len(unticked)} sign-off box(es) are "
                f"unticked. A human signs the spec before implementation starts — that sign-off is "
                f"the teaching checkpoint, not a formality."
            ),
            fix=[
                f"Ask the human to review {spec_path.as_posix()} and tick both boxes,",
                "then set `- **Status:** signed-off`.",
                f"Check it with:  python scripts/validate_spec.py {spec_path.as_posix()}",
            ],
            bypass_hint="create a file `.specs/BYPASS` saying why (it will be logged), then retry.",
            what=f"edit to {path} against unsigned spec {feature}",
        )

    return ALLOW


if __name__ == "__main__":
    raise SystemExit(main())
