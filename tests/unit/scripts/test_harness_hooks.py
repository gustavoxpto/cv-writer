"""The hooks are the only part of the harness that can actually stop an agent.

A hook that fails open is worse than no hook, because it is believed. These tests pin both
directions: it blocks what it should, and it stays out of the way otherwise.
"""

from __future__ import annotations

import io
import json

import _hook
import harness_lib
import pre_commit
import pre_edit_src
import pytest
from test_harness_lib import SPEC


@pytest.fixture(autouse=True)
def no_ambient_bypass(monkeypatch, tmp_path):
    """Never let the developer's own environment or a stray token file colour a result."""
    monkeypatch.delenv(harness_lib.BYPASS_TOKEN, raising=False)
    monkeypatch.setattr(harness_lib, "repo_root", lambda: tmp_path)
    monkeypatch.setattr(_hook, "log_bypass", lambda what: None)


def _event(monkeypatch, **payload):
    monkeypatch.setattr("sys.stdin", io.StringIO(json.dumps(payload)))


# ------------------------------------------------------------------------------ path scoping


def test_the_src_guard_only_looks_at_src():
    from pathlib import Path

    assert _hook.under(Path("C:/g/projetos/src/cv_writer/x.py"), "src")
    assert _hook.under(Path("src/cv_writer/x.py"), "src")
    assert not _hook.under(Path("tests/unit/test_x.py"), "src")
    assert not _hook.under(Path("scripts/gate.py"), "src")
    assert not _hook.under(None, "src")


def test_tests_and_docs_stay_editable_so_the_failing_test_can_be_written_first(monkeypatch):
    _event(monkeypatch, tool_name="Edit", tool_input={"file_path": "tests/unit/test_x.py"})
    assert pre_edit_src.main() == _hook.ALLOW


# --------------------------------------------------------------------- spec-before-code gate


def test_editing_src_with_no_current_feature_is_blocked(monkeypatch):
    monkeypatch.setattr(pre_edit_src, "current_feature", lambda: ("", ""))
    _event(monkeypatch, tool_name="Edit", tool_input={"file_path": "src/cv_writer/x.py"})
    assert pre_edit_src.main() == _hook.BLOCK


def test_editing_src_against_an_unsigned_spec_is_blocked(monkeypatch, tmp_path):
    feature = tmp_path / "099-example"
    feature.mkdir()
    draft = SPEC.replace("**Status:** signed-off", "**Status:** draft")
    (feature / "spec.md").write_text(draft, encoding="utf-8")
    monkeypatch.setattr(pre_edit_src, "current_feature", lambda: ("099-example", "execute"))
    monkeypatch.setattr(pre_edit_src, "feature_dir", lambda name: tmp_path / name)

    _event(monkeypatch, tool_name="Edit", tool_input={"file_path": "src/cv_writer/x.py"})
    assert pre_edit_src.main() == _hook.BLOCK


def test_editing_src_against_a_signed_spec_is_allowed(monkeypatch, tmp_path):
    feature = tmp_path / "099-example"
    feature.mkdir()
    (feature / "spec.md").write_text(SPEC, encoding="utf-8")
    monkeypatch.setattr(pre_edit_src, "current_feature", lambda: ("099-example", "execute"))
    monkeypatch.setattr(pre_edit_src, "feature_dir", lambda name: tmp_path / name)

    _event(monkeypatch, tool_name="Edit", tool_input={"file_path": "src/cv_writer/x.py"})
    assert pre_edit_src.main() == _hook.ALLOW


def test_a_bypass_token_file_opens_the_gate_and_is_logged(monkeypatch, tmp_path):
    logged: list[str] = []
    monkeypatch.setattr(_hook, "log_bypass", logged.append)
    specs = tmp_path / ".specs"
    specs.mkdir()
    (specs / "BYPASS").write_text("migrating a legacy module", encoding="utf-8")
    monkeypatch.setattr(pre_edit_src, "current_feature", lambda: ("", ""))

    _event(monkeypatch, tool_name="Edit", tool_input={"file_path": "src/cv_writer/x.py"})
    assert pre_edit_src.main() == _hook.ALLOW
    assert logged, "a bypass must never be silent"


# ---------------------------------------------------------------------------- commit message


def test_commit_messages_are_pulled_out_of_the_command():
    command = 'git commit -m "feat(x): do a thing"'
    assert pre_commit.extract_message(command) == "feat(x): do a thing"
    assert pre_commit.extract_message("git commit -m 'fix(y): repair it'") == "fix(y): repair it"
    assert pre_commit.extract_message("git commit") is None


def test_multiple_dash_m_flags_become_header_and_body():
    message = pre_commit.extract_message('git commit -m "feat(x): a" -m "the body"')
    assert message == "feat(x): a\n\nthe body"


def test_only_commits_are_inspected():
    assert pre_commit._IS_COMMIT_RE.search("git commit -m 'x'")
    assert pre_commit._IS_COMMIT_RE.search("git -C . commit -m 'x'")
    assert not pre_commit._IS_COMMIT_RE.search("git status")
    assert not pre_commit._IS_COMMIT_RE.search("echo 'commit later'")


def test_a_malformed_commit_message_is_blocked_before_the_gate_is_even_run(monkeypatch):
    def explode(*_args, **_kwargs):
        raise AssertionError("the gate should not run once the message is already invalid")

    monkeypatch.setattr(pre_commit.subprocess, "run", explode)
    _event(monkeypatch, tool_name="Bash", tool_input={"command": 'git commit -m "Fixed it."'})
    assert pre_commit.main() == _hook.BLOCK


def test_a_non_commit_command_is_never_touched(monkeypatch):
    _event(monkeypatch, tool_name="Bash", tool_input={"command": "pytest tests -q"})
    assert pre_commit.main() == _hook.ALLOW


def test_an_amend_is_left_alone(monkeypatch):
    _event(monkeypatch, tool_name="Bash", tool_input={"command": "git commit --amend --no-edit"})
    assert pre_commit.main() == _hook.ALLOW


def test_a_red_gate_blocks_a_well_formed_commit(monkeypatch):
    class Result:
        returncode = 1
        stdout = "gate(quick): FAIL"
        stderr = ""

    monkeypatch.setattr(pre_commit.subprocess, "run", lambda *a, **k: Result())
    command = 'git commit -m "feat(x): add a thing"'
    _event(monkeypatch, tool_name="Bash", tool_input={"command": command})
    assert pre_commit.main() == _hook.BLOCK


def test_a_green_gate_lets_a_well_formed_commit_through(monkeypatch):
    class Result:
        returncode = 0
        stdout = "gate(quick): PASS"
        stderr = ""

    monkeypatch.setattr(pre_commit.subprocess, "run", lambda *a, **k: Result())
    command = 'git commit -m "feat(x): add a thing"'
    _event(monkeypatch, tool_name="Bash", tool_input={"command": command})
    assert pre_commit.main() == _hook.ALLOW


def test_an_explicit_bypass_overrides_a_red_gate_and_is_logged(monkeypatch):
    logged: list[str] = []
    monkeypatch.setattr(_hook, "log_bypass", logged.append)

    class Result:
        returncode = 1
        stdout = "gate(quick): FAIL"
        stderr = ""

    monkeypatch.setattr(pre_commit.subprocess, "run", lambda *a, **k: Result())
    _event(
        monkeypatch,
        tool_name="Bash",
        tool_input={"command": 'HARNESS_BYPASS=1 git commit -m "feat(x): add a thing"'},
    )
    assert pre_commit.main() == _hook.ALLOW
    assert logged == ["commit on a red gate"]


# ------------------------------------------------------------------------------- robustness


def test_a_malformed_event_never_wedges_a_session(monkeypatch):
    monkeypatch.setattr("sys.stdin", io.StringIO("not json at all"))
    assert _hook.payload() == {}
