"""Criterion 34: all domain logic (profile, matching, generation, persistence) lives in
importable modules with no web-framework imports; the UI layer only calls into them.

AST-based (`ast.parse` -> walk `ast.Import`/`ast.ImportFrom`), not grep-based, per ADR 0005
decision 1: a grep for "fastapi" would false-positive on `ingestion/requirements.py`'s
`SKILL_TERMS` dictionary, which legitimately contains the string "fastapi" as a skill name to
match inside posting text, not an import. This test walks every module under the five core
packages (`profile`, `db`, `ingestion`, `matching`, `generation`) and fails, naming the
offending module and the exact import statement, the moment any of them imports a
web-framework module. `web/` itself is not scanned — it is expected to import these.

`ast.walk()` visits every node in the tree regardless of nesting, so a web-framework import
hidden inside a function body (not just at module level) is caught the same way a top-level one
is — a code-review pass on this slice checked that explicitly rather than assuming it. The same
pass also checked the more evasive route — `importlib.import_module("fastapi")` or
`__import__("fastapi")` instead of a real `import` statement, neither of which is an
`ast.Import`/`ast.ImportFrom` node — and found it *wasn't* covered, so `_dynamic_import_calls()`
below adds it: any call to `importlib.import_module(...)`, `import_module(...)` (if imported by
name), or `__import__(...)` whose first argument is a string literal naming a web-framework
module.
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


def _dynamic_import_call_name(node: ast.Call) -> str | None:
    """If `node` is `importlib.import_module(...)`, a bare `import_module(...)`, or
    `__import__(...)`, return the callee's name for a readable offender message; otherwise
    None. Doesn't try to resolve `import_module`'s own alias back to `importlib` — a bare name
    called `import_module` is suspicious enough in these five packages on its own."""
    func = node.func
    if isinstance(func, ast.Attribute) and func.attr == "import_module":
        return "importlib.import_module"
    if isinstance(func, ast.Name) and func.id in ("import_module", "__import__"):
        return func.id
    return None


def _web_framework_imports(module_path: Path) -> list[str]:
    """Every import statement *or dynamic-import call* in `module_path` that names a
    web-framework module, formatted for a readable assertion failure (offending module + the
    exact statement)."""
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
        elif isinstance(node, ast.Call):
            callee_name = _dynamic_import_call_name(node)
            if callee_name is None or not node.args:
                continue
            first_arg = node.args[0]
            if isinstance(first_arg, ast.Constant) and isinstance(first_arg.value, str):
                top_level = first_arg.value.split(".")[0]
                if top_level in WEB_FRAMEWORK_TOP_LEVEL_MODULES:
                    offenders.append(f"{callee_name}({first_arg.value!r})")

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


def test_the_guard_itself_catches_a_dynamic_importlib_import_module_call(tmp_path):
    # A code-review pass found the original ast.Import/ast.ImportFrom-only walk would miss
    # someone reaching for fastapi via importlib instead of a real import statement — this
    # proves _web_framework_imports() actually catches that route now, using a synthetic
    # module rather than a real violation planted in the core packages.
    offending_module = tmp_path / "sneaky.py"
    offending_module.write_text(
        'import importlib\n\nfastapi = importlib.import_module("fastapi")\n', encoding="utf-8"
    )

    offenders = _web_framework_imports(offending_module)

    assert offenders == ['importlib.import_module(\'fastapi\')']


def test_the_guard_itself_catches_a_dunder_import_call(tmp_path):
    offending_module = tmp_path / "sneaky.py"
    offending_module.write_text('starlette = __import__("starlette")\n', encoding="utf-8")

    offenders = _web_framework_imports(offending_module)

    assert offenders == ["__import__('starlette')"]


def test_the_guard_itself_catches_a_web_framework_import_hidden_inside_a_function_body(
    tmp_path,
):
    offending_module = tmp_path / "sneaky.py"
    offending_module.write_text(
        "def lazy():\n    import fastapi\n    return fastapi\n", encoding="utf-8"
    )

    offenders = _web_framework_imports(offending_module)

    assert offenders == ["import fastapi"]


def test_the_guard_does_not_flag_an_unrelated_dynamic_import(tmp_path):
    innocent_module = tmp_path / "innocent.py"
    innocent_module.write_text(
        'import importlib\n\nyaml = importlib.import_module("yaml")\n', encoding="utf-8"
    )

    assert _web_framework_imports(innocent_module) == []
