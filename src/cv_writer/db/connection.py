"""Connect to the embedded SQLite database, creating and migrating it on first use.

Criterion 31: the database file lives outside version control, its location is configurable,
and a fresh run against a missing database creates and migrates it without manual steps.

Location resolution (first match wins):
  1. an explicit path passed to connect()/get_db_path(),
  2. the CV_WRITER_DB_PATH environment variable,
  3. the default, data/cv_writer.sqlite3 — inside the data/ directory .gitignore already
     blocks wholesale (see .gitignore's "CV Writer personal data" section) and next to
     data/profile.yaml, since both hold real personal data (spec open question 6).

Migrations are ordered .sql scripts under migrations/ (ADR 0002: "schema migrations kept as
ordered SQL scripts under src/"), applied once each and recorded in schema_migrations so
re-running connect() against an already-migrated file is a no-op.
"""

from __future__ import annotations

import os
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

ENV_VAR = "CV_WRITER_DB_PATH"
DEFAULT_DB_PATH = Path("data") / "cv_writer.sqlite3"
MIGRATIONS_DIR = Path(__file__).parent / "migrations"


def get_db_path(override: str | Path | None = None) -> Path:
    """Resolve the database path: explicit override > CV_WRITER_DB_PATH > default."""
    if override is not None:
        return Path(override)
    env_value = os.environ.get(ENV_VAR)
    if env_value:
        return Path(env_value)
    return DEFAULT_DB_PATH


def connect(path: str | Path | None = None) -> sqlite3.Connection:
    """Open (creating and migrating if needed) the database at the resolved path."""
    db_path = get_db_path(path)
    db_path.parent.mkdir(parents=True, exist_ok=True)

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    migrate(conn)
    return conn


def migrate(conn: sqlite3.Connection) -> None:
    """Apply any migration under migrations/ not yet recorded in schema_migrations."""
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS schema_migrations (
            filename TEXT PRIMARY KEY,
            applied_at TEXT NOT NULL
        )
        """
    )
    applied = {row[0] for row in conn.execute("SELECT filename FROM schema_migrations")}

    for migration_path in sorted(MIGRATIONS_DIR.glob("*.sql")):
        if migration_path.name in applied:
            continue
        conn.executescript(migration_path.read_text(encoding="utf-8"))
        conn.execute(
            "INSERT INTO schema_migrations (filename, applied_at) VALUES (?, ?)",
            (migration_path.name, datetime.now(timezone.utc).isoformat()),
        )
        conn.commit()
