"""Spec 002 AC-006: widening what the extractor recognises introduces no model call.

Spec 001's criterion 14 says scoring is deterministic — the same posting and profile always
produce the same report, with no model involved. Spec 002 makes the extractor recognise a great
deal more, and the obvious way to have done that would have been to reach for an LLM. This file
is the sensor that says we did not, and that nobody does later without it failing.

Two independent checks, because either alone has a hole. The AST scan catches an import that no
test happens to execute, including one hidden inside a function body or smuggled in through
`importlib.import_module`. The patched-socket run catches the opposite case — anything that
actually reaches the network at runtime, whatever it imported to get there. Structure and
behaviour, not one standing in for the other.

The AST half is modelled on tests/unit/web/test_core_has_no_web_imports.py, including that
file's own hard-won handling of dynamic imports; see its docstring for why a grep is not enough.
"""

from __future__ import annotations

import ast
import socket
from datetime import date
from pathlib import Path

import pytest

from cv_writer.ingestion.models import RequirementKind
from cv_writer.ingestion.requirements import extract_requirements
from cv_writer.matching.matcher import build_match_report
from cv_writer.profile.models import Bullet, Identity, JobHistory, Language, Metric, Profile, Skill

SRC_ROOT = Path(__file__).resolve().parents[3] / "src" / "cv_writer"

# The packages that make up the extract-to-score path AC-006 is about. Generation legitimately
# calls a model and is deliberately not scanned.
DETERMINISTIC_PACKAGES = ("ingestion", "matching")

# Every module name a model call could plausibly arrive through. `anthropic` is the real one —
# it is already a project dependency for generation, so nothing stops an import here but this
# test. The others are listed so a future contributor reaching for a different provider trips
# the same wire rather than finding it only guards one vendor.
MODEL_CLIENT_TOP_LEVEL_MODULES = {
    "anthropic",
    "openai",
    "cohere",
    "google",
    "litellm",
    "ollama",
    "transformers",
}

SPANISH_POSTING = """
Consultor de Formación

Requisitos:
- Experiencia en gestión de proyectos
- Se requiere inglés

Se valorará:
- Conocimientos de consultoría estratégica
"""


def _deterministic_module_paths() -> list[Path]:
    paths: list[Path] = []
    for package in DETERMINISTIC_PACKAGES:
        paths.extend(sorted((SRC_ROOT / package).rglob("*.py")))
    return paths


def _dynamic_import_call_name(node: ast.Call) -> str | None:
    """`importlib.import_module(...)`, a bare `import_module(...)`, or `__import__(...)` —
    none of which is an ast.Import node, and all of which would otherwise walk straight past
    the scan below."""
    func = node.func
    if isinstance(func, ast.Attribute) and func.attr == "import_module":
        return "importlib.import_module"
    if isinstance(func, ast.Name) and func.id in ("import_module", "__import__"):
        return func.id
    return None


def _model_client_imports(module_path: Path) -> list[str]:
    """Every import statement or dynamic-import call in `module_path` naming a model client,
    formatted so a failure names the offending statement rather than just the file."""
    tree = ast.parse(module_path.read_text(encoding="utf-8"), filename=str(module_path))

    offenders: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name.split(".")[0] in MODEL_CLIENT_TOP_LEVEL_MODULES:
                    offenders.append(f"import {alias.name}")
        elif isinstance(node, ast.ImportFrom) and node.module:
            if node.module.split(".")[0] in MODEL_CLIENT_TOP_LEVEL_MODULES:
                names = ", ".join(alias.name for alias in node.names)
                offenders.append(f"from {node.module} import {names}")
        elif isinstance(node, ast.Call):
            callee = _dynamic_import_call_name(node)
            if callee is None or not node.args:
                continue
            first_arg = node.args[0]
            if isinstance(first_arg, ast.Constant) and isinstance(first_arg.value, str):
                if first_arg.value.split(".")[0] in MODEL_CLIENT_TOP_LEVEL_MODULES:
                    offenders.append(f"{callee}({first_arg.value!r})")

    return offenders


_MODULE_PATHS = _deterministic_module_paths()


@pytest.mark.parametrize(
    "module_path",
    _MODULE_PATHS,
    ids=[str(p.relative_to(SRC_ROOT)) for p in _MODULE_PATHS],
)
def test_deterministic_module_imports_no_model_client(module_path: Path):
    """AC-006: nothing on the extract-to-score path imports a model client."""
    offenders = _model_client_imports(module_path)

    assert offenders == [], (
        f"{module_path.relative_to(SRC_ROOT)} imports a model client (AC-006 / spec 001 "
        f"criterion 14 violation): {offenders}"
    )


def test_at_least_the_expected_modules_were_scanned():
    """parametrize over an empty list passes trivially, so a path typo would turn the test above
    into decoration. Same guard the web-boundary test carries, for the same reason."""
    scanned = {str(p.relative_to(SRC_ROOT)).replace("\\", "/") for p in _MODULE_PATHS}

    assert "ingestion/requirements.py" in scanned
    assert "ingestion/term_list.py" in scanned
    assert "matching/matcher.py" in scanned
    assert len(_MODULE_PATHS) > 5


def test_the_scan_itself_catches_a_planted_model_import(tmp_path: Path):
    """The check has to be shown to fail on the thing it claims to catch, or a passing run
    proves only that the scan found nothing anywhere — including because it looks for the wrong
    thing. Covers all three shapes: plain import, from-import, and dynamic."""
    planted = tmp_path / "planted.py"
    planted.write_text(
        "import importlib\n"
        "import anthropic\n"
        "from openai import OpenAI\n"
        "def late():\n"
        "    import cohere\n"
        "    return importlib.import_module('litellm')\n",
        encoding="utf-8",
    )

    offenders = _model_client_imports(planted)

    assert "import anthropic" in offenders
    assert "from openai import OpenAI" in offenders
    assert "import cohere" in offenders, "an import inside a function body was missed"
    assert "importlib.import_module('litellm')" in offenders


def _profile() -> Profile:
    """Minimal valid profile: one history with the required metric, one evidenced skill, one
    language. Built in memory so this test touches no disk beyond the term file itself."""
    bullets = [
        Bullet(
            id=f"bullet-{n}",
            situation="situation",
            task="task",
            action="action, running gestión de proyectos work",
            result="result",
            metric=Metric(value="100%", unit="coverage") if n == 1 else None,
        )
        for n in (1, 2, 3)
    ]
    return Profile(
        identity=Identity(name="Ana Example", email="ana@example.com"),
        languages=[Language(name="English", proficiency="professional")],
        job_histories=[
            JobHistory(
                id="job-1",
                company="Acme",
                role_title="Consultant",
                country="Portugal",
                area="Training",
                start_date=date(2020, 1, 15),
                end_date="present",
                bullets=bullets,
            )
        ],
        skills=[Skill(name="Project Planning", category="method", evidence=["job-1"])],
    )


def test_extract_and_score_complete_with_the_network_unavailable(monkeypatch: pytest.MonkeyPatch):
    """AC-006 as behaviour rather than structure: with sockets dead, a Spanish posting still
    extracts and still scores. Any model call — however it was imported — would raise here."""

    def _no_sockets(*args, **kwargs):
        raise AssertionError("the extract-to-score path opened a socket; AC-006 forbids it")

    monkeypatch.setattr(socket, "socket", _no_sockets)
    monkeypatch.setattr(socket, "create_connection", _no_sockets)

    requirement_set = extract_requirements(SPANISH_POSTING)
    report = build_match_report(_profile(), requirement_set, reference_date=date(2026, 8, 20))

    # Assert real output, not merely "it did not raise" — a no-exception check would pass on an
    # empty result, which is precisely the quiet failure L-004 is about.
    values = {r.value for r in requirement_set.requirements}
    assert "project planning" in values
    assert "english" in {
        r.value for r in requirement_set.of_kind(RequirementKind.LANGUAGE)
    }
    assert len(report.matches) == len(requirement_set.requirements)
    assert 0.0 <= report.score <= 100.0


def test_scoring_is_repeatable(monkeypatch: pytest.MonkeyPatch):
    """AC-006 preserves criterion 14, which is about determinism, not only about abstinence from
    models. A cached or seeded model call would satisfy the socket test on a second run; two
    identical scores from two independent extractions would not survive a nondeterministic one."""
    profile = _profile()
    reference = date(2026, 8, 20)

    first = build_match_report(
        profile, extract_requirements(SPANISH_POSTING), reference_date=reference
    )
    second = build_match_report(
        profile, extract_requirements(SPANISH_POSTING), reference_date=reference
    )

    assert first.score == second.score
    assert [m.requirement.value for m in first.matches] == [
        m.requirement.value for m in second.matches
    ]
    assert [m.status for m in first.matches] == [m.status for m in second.matches]
