"""Criterion 34: all domain logic (profile, matching, generation, persistence) lives in
importable modules with no web-framework imports; the UI layer only calls into them.

AST-based (`ast.parse` -> walk `ast.Import`/`ast.ImportFrom`), not grep-based, per ADR 0005
decision 1: a grep for "fastapi" would false-positive on `ingestion/requirements.py`'s
`SKILL_TERMS` dictionary, which legitimately contains the string "fastapi" as a skill name to
match inside posting text, not an import. This test walks every module under the five core
packages (`profile`, `db`, `ingestion`, `matching`, `generation`) and fails, naming the
offending module and the exact import statement, the moment any of them imports a
web-framework module. `web/` itself is not scanned — it is expected to import these.
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

SRC_ROOT = Path(__file__).resolve().parents[3] / "src" / "cv_writer"
CORE_PACKAGES = ["profile", "db", "ingestion", "matching", "generation"]

# The concrete import names a web-framework dependency could be reached through. `multipart` /
# `python_multipart` covers python-multipart's importable module name (used by fastapi/
# starlette for form parsing).
WEB_FRAMEWORK_TOP_LEVEL_MODULES = {
    "fastapi",
    "starlette",
    "uvicorn",
    "multipart",
    "python_multipart",
}


def _core_module_paths() -> list[Path]:
    paths: list[Path] = []
    for package in CORE_PACKAGES:
        paths.extend(sorted((SRC_ROOT / package).rglob("*.py")))
    return paths


def _web_framework_imports(module_path: Path) -> list[str]:
    """Every import statement in `module_path` that names a web-framework module, formatted
    for a readable assertion failure (offending module + the exact statement)."""
    tree = ast.parse(module_path.read_text(encoding="utf-8"), filename=str(module_path))

    offenders: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                top_level = alias.name.split(".")[0]
                if top_level in WEB_FRAMEWORK_TOP_LEVEL_MODULES:
                    offenders.append(f"import {alias.name}")
        elif isinstance(node, ast.ImportFrom) and node.module:
            top_level = node.module.split(".")[0]
            if top_level in WEB_FRAMEWORK_TOP_LEVEL_MODULES:
                names = ", ".join(alias.name for alias in node.names)
                offenders.append(f"from {node.module} import {names}")

    return offenders


_MODULE_PATHS = _core_module_paths()


@pytest.mark.parametrize(
    "module_path",
    _MODULE_PATHS,
    ids=[str(p.relative_to(SRC_ROOT)) for p in _MODULE_PATHS],
)
def test_core_module_imports_no_web_framework(module_path):
    offenders = _web_framework_imports(module_path)

    assert offenders == [], (
        f"{module_path.relative_to(SRC_ROOT)} imports a web-framework module (criterion 34 "
        f"violation): {offenders}"
    )


def test_at_least_one_core_module_was_actually_scanned():
    # A guard against this test silently passing because CORE_PACKAGES resolved to nothing
    # (e.g. a path typo) — pytest.mark.parametrize with an empty list "passes" trivially.
    assert len(_MODULE_PATHS) > 10
