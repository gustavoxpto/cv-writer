"""Shared parsing and reporting helpers for the harness sensors.

Every validator in ``scripts/`` is a *sensor*: it looks at an artifact and exits 0 or non-zero.
Nothing here decides anything by judgement — the whole point (CLAUDE.md hard rule #4) is that a
tool, not an agent, gets to say whether something passed.

The parsers are deliberately pure functions over text so they can be unit-tested without
touching the filesystem. See ``tests/unit/scripts/``.
"""

from __future__ import annotations

import os
import re
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path

# Windows consoles default to a legacy codepage that cannot render the em dashes and ellipses
# these artifacts are full of. Without this, a sensor can fail on its own output.
for _stream in (sys.stdout, sys.stderr):
    if hasattr(_stream, "reconfigure"):
        _stream.reconfigure(encoding="utf-8", errors="replace")

# --------------------------------------------------------------------------------------
# Placeholder detection
# --------------------------------------------------------------------------------------

# A spec that still contains template scaffolding has not been written, it has been copied.
# `<like-this>` catches angle-bracket placeholders without catching real comparisons ("< 200ms"),
# because the bracket must be followed by a letter.
_UNFILLED_PATTERNS = (
    re.compile(r"<[A-Za-z][^>\n]*>"),
    re.compile(r"\b(TODO|TBD|FIXME|XXX)\b"),
)

# An ellipsis in a one-line criterion means "not finished". In a paragraph of prose it usually
# means an elided quotation, which is legitimate — so these only apply outside prose sections.
_ELLIPSIS_PATTERNS = (
    re.compile(r"…"),
    re.compile(r"\.\.\."),
)


def find_placeholders(text: str, prose: bool = False) -> list[str]:
    """Return every placeholder-looking fragment in *text*, in order of appearance.

    Set *prose* for long-form sections such as `## Why`, where an ellipsis inside a quotation is
    normal writing rather than an unfinished sentence.
    """
    patterns = _UNFILLED_PATTERNS if prose else _UNFILLED_PATTERNS + _ELLIPSIS_PATTERNS
    found: list[str] = []
    for pattern in patterns:
        found.extend(match.group(0) for match in pattern.finditer(text))
    return found


def strip_html_comments(text: str) -> str:
    """Drop `<!-- ... -->` blocks.

    Templates carry their instructions in HTML comments, which are full of deliberate
    placeholders. Those must never count against a real artifact that kept the comment.
    """
    return re.sub(r"<!--.*?-->", "", text, flags=re.DOTALL)


# --------------------------------------------------------------------------------------
# Generic markdown helpers
# --------------------------------------------------------------------------------------

_SECTION_RE = re.compile(r"^##\s+(.+?)\s*$", re.MULTILINE)
_META_RE = re.compile(r"^\s*-\s+\*\*(?P<key>[^:*]+):\*\*\s*(?P<value>.*?)\s*$", re.MULTILINE)

# Matches "- **AC-001** — text", tolerating any of the dashes people actually type.
_DASH = r"[—–:-]"


def sections(text: str) -> list[str]:
    """Every level-2 heading, in document order."""
    return _SECTION_RE.findall(text)


def section_body(text: str, name: str) -> str:
    """The text under level-2 heading *name*, up to the next level-2 heading. '' if absent."""
    pattern = re.compile(
        rf"^##\s+{re.escape(name)}\s*$(?P<body>.*?)(?=^##\s|\Z)",
        re.MULTILINE | re.DOTALL,
    )
    match = pattern.search(text)
    return match.group("body") if match else ""


def metadata(text: str) -> dict[str, str]:
    """The `- **Key:** value` header lines, lowercased keys."""
    return {
        m.group("key").strip().lower(): m.group("value").strip()
        for m in _META_RE.finditer(text)
    }


def checkboxes(text: str) -> list[tuple[bool, str]]:
    """Every `- [ ]` / `- [x]` line as (checked, label)."""
    out: list[tuple[bool, str]] = []
    box_re = re.compile(r"^\s*-\s+\[(?P<box>[ xX])\]\s*(?P<label>.*?)\s*$", re.MULTILINE)
    for match in box_re.finditer(text):
        out.append((match.group("box").lower() == "x", match.group("label")))
    return out


def _sub_fields(block: str) -> dict[str, str]:
    """Indented `- **Key:** value` lines belonging to a list item."""
    return {
        m.group("key").strip().lower(): m.group("value").strip()
        for m in _META_RE.finditer(block)
    }


def _split_items(text: str, id_prefix: str) -> list[tuple[str, str, bool, str]]:
    """Split *text* into (id, title, checked, body) for every `- [ ] **XX-001** — title` item."""
    item_re = re.compile(
        rf"^\s*-\s+(?:\[(?P<box>[ xX])\]\s+)?\*\*(?P<id>{id_prefix}-\d+)\*\*\s*{_DASH}?\s*"
        rf"(?P<title>.*?)\s*$",
        re.MULTILINE,
    )
    matches = list(item_re.finditer(text))
    items: list[tuple[str, str, bool, str]] = []
    for index, match in enumerate(matches):
        end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
        body = text[match.end() : end]
        checked = (match.group("box") or " ").lower() == "x"
        items.append((match.group("id"), match.group("title"), checked, body))
    return items


def _item_text(title: str, body: str) -> str:
    """Join a list item's first line with its wrapped continuation lines.

    Criteria wrap. Without this, `- **AC-003** — WHEN a posting contains …` followed by an
    indented second line holding the SHALL would be read as a criterion with no SHALL at all —
    the validator would reject correct specs and, worse, teach people to write one-line criteria
    to keep it quiet.

    Stops at the first blank line, and skips `- **Key:** value` sub-fields, which belong to the
    item's structure rather than its prose.
    """
    parts = [title]
    lines = body.split("\n")
    if lines and not lines[0].strip():
        # The body starts at the end of the title's own line, so drop that empty remainder —
        # otherwise every item looks like it terminates immediately.
        lines = lines[1:]
    for line in lines:
        if not line.strip():
            break
        if _META_RE.match(line):
            continue
        parts.append(line.strip())
    return " ".join(parts).strip()


def criterion_ids(text: str) -> list[str]:
    """Every `AC-NNN` mentioned in *text*, de-duplicated, in order."""
    seen: dict[str, None] = {}
    for match in re.finditer(r"\bAC-\d+\b", text):
        seen.setdefault(match.group(0), None)
    return list(seen)


# --------------------------------------------------------------------------------------
# Parsed artifacts
# --------------------------------------------------------------------------------------


@dataclass
class Criterion:
    id: str
    text: str


@dataclass
class Spec:
    status: str = ""
    size: str = ""
    criteria: list[Criterion] = field(default_factory=list)
    section_names: list[str] = field(default_factory=list)
    blocking_open_questions: list[str] = field(default_factory=list)
    signoff_boxes: list[tuple[bool, str]] = field(default_factory=list)

    @property
    def criterion_ids(self) -> list[str]:
        return [c.id for c in self.criteria]

    @property
    def signed_off(self) -> bool:
        return (
            self.status == "signed-off"
            and bool(self.signoff_boxes)
            and all(checked for checked, _ in self.signoff_boxes)
        )


def parse_spec(text: str) -> Spec:
    body = strip_html_comments(text)
    meta = metadata(body)
    criteria = [
        Criterion(id=item_id, text=_item_text(title, sub))
        for item_id, title, _checked, sub in _split_items(
            section_body(body, "Acceptance criteria"), "AC"
        )
    ]
    blocking = [
        label
        for _checked, label in checkboxes(section_body(body, "Open questions"))
        if "(blocking)" in label.lower()
    ]
    unresolved_blocking = [
        label
        for checked, label in checkboxes(section_body(body, "Open questions"))
        if "(blocking)" in label.lower() and not checked
    ]
    del blocking
    return Spec(
        status=meta.get("status", "").strip().lower(),
        size=meta.get("size", "").strip().lower(),
        criteria=criteria,
        section_names=sections(body),
        blocking_open_questions=unresolved_blocking,
        signoff_boxes=checkboxes(section_body(body, "Sign-off")),
    )


@dataclass
class Task:
    id: str
    title: str
    done: bool
    covers: list[str]
    files: list[str]
    gate: str
    done_when: str


@dataclass
class Tasks:
    tasks: list[Task] = field(default_factory=list)
    coverage_matrix_ids: list[str] = field(default_factory=list)


VALID_GATES = ("quick", "full", "build")


def parse_tasks(text: str) -> Tasks:
    body = strip_html_comments(text)
    tasks: list[Task] = []
    # Everything before the coverage matrix is task definitions; the matrix mentions AC ids too
    # and would otherwise pollute the per-task "covers" fields.
    definitions = body.split("## Coverage matrix")[0]
    for task_id, title, checked, sub in _split_items(definitions, "T"):
        fields_ = _sub_fields(sub)
        tasks.append(
            Task(
                id=task_id,
                title=title,
                done=checked,
                covers=criterion_ids(fields_.get("covers", "")),
                files=[f.strip(" `") for f in fields_.get("files", "").split(",") if f.strip(" `")],
                gate=fields_.get("gate", "").strip().lower(),
                done_when=fields_.get("done when", "").strip(),
            )
        )
    matrix_ids = criterion_ids(section_body(body, "Coverage matrix"))
    return Tasks(tasks=tasks, coverage_matrix_ids=matrix_ids)


@dataclass
class ContractItem:
    id: str
    title: str
    done: bool
    verifies: list[str]
    check: str


@dataclass
class Contract:
    signed: bool = False
    items: list[ContractItem] = field(default_factory=list)


def parse_contract(text: str) -> Contract:
    body = strip_html_comments(text)
    signature_boxes = checkboxes(section_body(body, "Signature"))
    items = []
    for item_id, title, checked, sub in _split_items(section_body(body, "What will be built"), "C"):
        fields_ = _sub_fields(sub)
        items.append(
            ContractItem(
                id=item_id,
                title=title,
                done=checked,
                verifies=criterion_ids(fields_.get("verifies", "")),
                check=fields_.get("check", "").strip(),
            )
        )
    return Contract(
        signed=bool(signature_boxes) and all(checked for checked, _ in signature_boxes),
        items=items,
    )


@dataclass
class Validation:
    verdict: str = ""
    score_rows: list[list[str]] = field(default_factory=list)
    evidence: dict[str, str] = field(default_factory=dict)


_EVIDENCE_RE = re.compile(r"`?(?P<path>[\w./\\-]+\.[A-Za-z0-9]+):(?P<line>\d+)`?")


def parse_validation(text: str) -> Validation:
    body = strip_html_comments(text)
    meta = metadata(body)
    score_rows = _table_rows(section_body(body, "Score"))
    evidence: dict[str, str] = {}
    for row in _table_rows(section_body(body, "Criterion evidence")):
        joined = " | ".join(row)
        ids = criterion_ids(joined)
        match = _EVIDENCE_RE.search(joined)
        if ids and match:
            evidence[ids[0]] = f"{match.group('path')}:{match.group('line')}"
    return Validation(
        verdict=meta.get("verdict", "").strip().upper(),
        score_rows=score_rows,
        evidence=evidence,
    )


def _table_rows(text: str) -> list[list[str]]:
    """Body rows of the first markdown table in *text* (header and separator dropped)."""
    rows: list[list[str]] = []
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped.startswith("|"):
            continue
        cells = [cell.strip() for cell in stripped.strip("|").split("|")]
        if all(set(cell) <= set("-: ") for cell in cells):  # separator row
            continue
        rows.append(cells)
    return rows[1:] if rows else []  # drop the header row


# --------------------------------------------------------------------------------------
# Reporting
# --------------------------------------------------------------------------------------


@dataclass
class Report:
    """Collected findings for one sensor run. Non-empty errors means a non-zero exit."""

    name: str
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    def error(self, message: str) -> None:
        self.errors.append(message)

    def warn(self, message: str) -> None:
        self.warnings.append(message)

    @property
    def ok(self) -> bool:
        return not self.errors

    def emit(self) -> int:
        """Print the findings and return the exit code."""
        for message in self.warnings:
            print(f"  warn  {message}")
        for message in self.errors:
            print(f"  FAIL  {message}")
        if self.ok:
            note = f" ({len(self.warnings)} warning(s))" if self.warnings else ""
            print(f"{self.name}: PASS{note}")
            return 0
        print(f"{self.name}: FAIL ({len(self.errors)} problem(s))")
        return 1


# --------------------------------------------------------------------------------------
# Repo / environment
# --------------------------------------------------------------------------------------


def repo_root() -> Path:
    return Path(__file__).resolve().parent.parent


def feature_dir(feature: str) -> Path:
    return repo_root() / ".specs" / "features" / feature


def python_executable() -> str:
    """The interpreter to run tools with — prefer this repo's venv over whatever invoked us."""
    root = repo_root()
    for candidate in (root / ".venv" / "Scripts" / "python.exe", root / ".venv" / "bin" / "python"):
        if candidate.exists():
            return str(candidate)
    return sys.executable


def run(command: list[str]) -> int:
    """Run *command* from the repo root, streaming output. Returns its exit code."""
    print(f"$ {' '.join(command)}")
    return subprocess.call(command, cwd=str(repo_root()))


BYPASS_TOKEN = "HARNESS_BYPASS"


def bypass_requested(command: str = "") -> bool:
    """Is a blocking gate being deliberately overridden?

    Three routes, because hooks and tools see different things:
      * the environment, for a whole session (`HARNESS_BYPASS=1`)
      * the command string itself, for one command (`HARNESS_BYPASS=1 git commit ...`)
      * a `.specs/BYPASS` token file, for tool calls that carry no command at all (Edit/Write)

    All three are equally loud: every one of them gets written to the bypass log.
    """
    if os.environ.get(BYPASS_TOKEN, "").strip() not in ("", "0", "false", "False"):
        return True
    if BYPASS_TOKEN in command:
        return True
    return (repo_root() / ".specs" / "BYPASS").exists()


def log_bypass(what: str) -> None:
    """Append a bypass to STATE.md. Bypassing is allowed; bypassing silently is not."""
    from datetime import date

    state = repo_root() / ".specs" / "STATE.md"
    if not state.exists():
        return
    text = state.read_text(encoding="utf-8")
    marker = "<!-- bypass-log -->"
    entry = f"- {date.today().isoformat()} — HARNESS_BYPASS used to override: {what}"
    if marker in text:
        text = text.replace(marker, f"{entry}\n\n{marker}")
    else:
        text = text.rstrip() + f"\n\n{entry}\n"
    state.write_text(text, encoding="utf-8")


def current_feature() -> tuple[str, str]:
    """(feature, phase) from STATE.md's `## Current` block. ('', '') if unset."""
    state = repo_root() / ".specs" / "STATE.md"
    if not state.exists():
        return "", ""
    meta = metadata(section_body(strip_html_comments(state.read_text(encoding="utf-8")), "Current"))
    return meta.get("feature", "").strip(), meta.get("phase", "").strip().lower()
