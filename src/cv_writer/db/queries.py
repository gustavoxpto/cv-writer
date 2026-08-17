"""Cross-referencing queries over the profile-derived tables (spec criterion 6's own examples:
"every bullet evidencing Python", "all histories in Portugal"). Pure read queries, no I/O
beyond the given connection — callers own connect()/load_profile_into_db()."""

from __future__ import annotations

import sqlite3


def bullets_evidencing_skill(conn: sqlite3.Connection, skill_name: str) -> list[sqlite3.Row]:
    """Every bullet belonging to a job history that evidences `skill_name`."""
    return conn.execute(
        """
        SELECT b.*
        FROM bullets b
        JOIN skill_evidence se ON se.job_history_id = b.job_history_id
        JOIN skills s ON s.id = se.skill_id
        WHERE s.name = ?
        ORDER BY b.job_history_id, b.position
        """,
        (skill_name,),
    ).fetchall()


def histories_in_country(conn: sqlite3.Connection, country: str) -> list[sqlite3.Row]:
    """Every job history whose country matches exactly."""
    return conn.execute(
        "SELECT * FROM job_histories WHERE country = ? ORDER BY start_date",
        (country,),
    ).fetchall()
