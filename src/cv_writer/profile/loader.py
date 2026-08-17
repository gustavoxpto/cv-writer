"""Load data/profile.yaml (or any profile source) into a validated Profile.

Criterion 1: loading a file that violates the schema fails with an error naming the
offending field and path, and never yields a partially-loaded profile. Pydantic already
never returns a partial model on failure (validation raises before construction), so the
only work here is turning its ValidationError into a message that names the path, and
doing the same for "the YAML itself doesn't parse" / "the YAML isn't a mapping" — failure
modes Pydantic never sees because they happen before validation starts.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml
from pydantic import ValidationError

from .errors import ProfileValidationError
from .models import Profile


def load_profile(path: str | Path) -> Profile:
    """Load and validate a profile from a YAML file. Raises ProfileValidationError."""
    path = Path(path)
    try:
        raw_text = path.read_text(encoding="utf-8")
    except OSError as exc:
        raise ProfileValidationError(f"could not read profile at {path}: {exc}") from exc

    return _load_profile_text(raw_text, source=str(path))


def load_profile_dict(data: dict[str, Any], *, source: str = "<dict>") -> Profile:
    """Validate an already-parsed mapping (used by tests and by future DB/UI callers
    that build a profile dict without going through YAML)."""
    return _validate(data, source=source)


def _load_profile_text(raw_text: str, *, source: str) -> Profile:
    try:
        data = yaml.safe_load(raw_text)
    except yaml.YAMLError as exc:
        raise ProfileValidationError(f"{source}: not valid YAML — {exc}") from exc

    if not isinstance(data, dict):
        raise ProfileValidationError(
            f"{source}: root of a profile must be a mapping (got "
            f"{type(data).__name__ if data is not None else 'empty document'})"
        )

    return _validate(data, source=source)


def _validate(data: dict[str, Any], *, source: str) -> Profile:
    try:
        return Profile.model_validate(data)
    except ValidationError as exc:
        raise ProfileValidationError(_format_validation_error(exc, source=source)) from exc


def _format_validation_error(exc: ValidationError, *, source: str) -> str:
    lines = [f"{source}: profile failed validation ({exc.error_count()} error(s)):"]
    for error in exc.errors():
        path = ".".join(str(part) for part in error["loc"]) or "<root>"
        lines.append(f"  - {path}: {error['msg']}")
    return "\n".join(lines)
