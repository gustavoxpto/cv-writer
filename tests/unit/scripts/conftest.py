"""Put `scripts/` and `scripts/hooks/` on the import path.

The sensors are not part of the installed package (`pyproject.toml` only ships `src/`), so they
are imported by path here rather than by distribution.
"""

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]

for directory in (REPO_ROOT / "scripts", REPO_ROOT / "scripts" / "hooks"):
    if str(directory) not in sys.path:
        sys.path.insert(0, str(directory))
