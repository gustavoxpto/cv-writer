"""Design boundary B1 / contract C-007: after T-007, render_text.py owns no user-visible
word of its own -- every heading string a reader of the CV would see comes from
headings.py, keyed by cv.language. A blacklist of the three old English words would only
catch the words we already found; this scans for *any* literal English word left in the
module, so the next one is caught too (OQ-5's "if a later slice adds a fourth section, it
adds a criterion with it" is only a promise until something enforces it).

AST-based (ast.parse, walk ast.Constant -- which ast.walk() already descends into for the
literal parts of an f-string's ast.JoinedStr, verified below), modelled on
tests/unit/web/test_core_has_no_web_imports.py, including that file's two habits worth
copying: a synthetic-violation case proving the scan catches what it claims to, and a guard
asserting the scan actually looked at a real, non-empty file.
"""

from __future__ import annotations

import ast
import re
from pathlib import Path

RENDER_TEXT_PATH = (
    Path(__file__).resolve().parents[3]
    / "src"
    / "cv_writer"
    / "generation"
    / "render_text.py"
)

# Two or more consecutive ASCII letters -- catches a whole word, not a single letter used as
# punctuation (there is none of that here, but the rule is about words, not letters).
_WORD_PATTERN = re.compile(r"[A-Za-z]{2,}")


def _docstring_constant_ids(tree: ast.Module) -> set[int]:
    """The id()s of every module- and function-level docstring Constant node, so the literal
    scan below can skip them -- docstrings are for maintainers reading the source, not for a
    reader of the rendered CV."""
    docstring_ids: set[int] = set()

    def _mark_docstring(body: list[ast.stmt]) -> None:
        if not body:
            return
        first = body[0]
        if (
            isinstance(first, ast.Expr)
            and isinstance(first.value, ast.Constant)
            and isinstance(first.value.value, str)
        ):
            docstring_ids.add(id(first.value))

    _mark_docstring(tree.body)
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            _mark_docstring(node.body)

    return docstring_ids


def _hardcoded_word_literals(module_path: Path) -> list[str]:
    """Every string literal (including an f-string's literal parts -- ast.walk() already
    descends into ast.JoinedStr.values as ordinary ast.Constant nodes, so no separate
    JoinedStr branch is needed) in `module_path` containing two or more consecutive ASCII
    letters, skipping docstrings. Empty if the module owns no user-visible words of its own.
    """
    source = module_path.read_text(encoding="utf-8")
    tree = ast.parse(source, filename=str(module_path))
    skip_ids = _docstring_constant_ids(tree)

    offenders: list[str] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Constant) or not isinstance(node.value, str):
            continue
        if id(node) in skip_ids:
            continue
        if _WORD_PATTERN.search(node.value):
            offenders.append(node.value)

    return offenders


def test_render_text_owns_no_hardcoded_user_visible_word():
    offenders = _hardcoded_word_literals(RENDER_TEXT_PATH)

    assert offenders == [], (
        "render_text.py has a string literal containing a word of its own (design "
        f"boundary B1 violation -- every heading must come from headings.py): {offenders}"
    )


def test_the_scan_looked_at_a_real_non_empty_file():
    # A guard against this test silently passing because RENDER_TEXT_PATH resolved to
    # nothing or an empty file (e.g. a path typo).
    assert RENDER_TEXT_PATH.exists()
    assert len(RENDER_TEXT_PATH.read_text(encoding="utf-8")) > 100


def test_the_scan_catches_a_planted_synthetic_violation(tmp_path):
    offending_module = tmp_path / "sneaky.py"
    offending_module.write_text(
        '"""A harmless module docstring, correctly ignored."""\n\n'
        "def render():\n"
        '    """A harmless function docstring, also ignored."""\n'
        '    return "## Experience"\n',
        encoding="utf-8",
    )

    offenders = _hardcoded_word_literals(offending_module)

    assert offenders == ["## Experience"]


def test_the_scan_catches_a_planted_word_inside_an_f_string(tmp_path):
    offending_module = tmp_path / "sneaky_fstring.py"
    offending_module.write_text(
        "def render(name):\n"
        '    return f"## Skills for {name}"\n',
        encoding="utf-8",
    )

    offenders = _hardcoded_word_literals(offending_module)

    assert offenders == ["## Skills for "]


def test_the_scan_does_not_flag_pure_punctuation_and_whitespace_literals(tmp_path):
    innocent_module = tmp_path / "innocent.py"
    lines = ["# ", "## ", " | ", ": ", ", ", "- ", "#", "", chr(10)]
    source = "lines = " + repr(lines) + chr(10)
    innocent_module.write_text(source, encoding="utf-8")

    assert _hardcoded_word_literals(innocent_module) == []
