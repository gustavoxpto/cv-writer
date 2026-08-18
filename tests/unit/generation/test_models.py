"""Validation on the generation package's own domain models — not any one module's
behavior, so it gets its own small test file rather than living under extra_input's or
source_ids' tests."""

import pytest
from pydantic import ValidationError

from cv_writer.generation.models import ExtraInput, ExtraInputKind


def test_purely_numeric_extra_input_id_fails_validation():
    # Regression: same DB-coercion risk as profile.models.Bullet.id (both flow into
    # db.application_bullet_sources.profile_bullet_id, declared INTEGER — ADR 0004
    # decision 1) — a purely-digit id silently becomes a SQLite INTEGER on round-trip.
    with pytest.raises(ValidationError, match="purely numeric"):
        ExtraInput(id="1", kind=ExtraInputKind.EMPHASIS, text="Some emphasis")
