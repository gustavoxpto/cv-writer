"""Criterion 6: the validated profile is loaded into the embedded database so skills and
histories can be queried and cross-referenced (e.g. "every bullet evidencing Python", "all
histories in Portugal"). The database copy is derived and rebuildable from data/profile.yaml;
re-running the load is idempotent and does not duplicate rows."""

from pathlib import Path

from cv_writer.db import connect, load_profile_into_db
from cv_writer.db.queries import bullets_evidencing_skill, histories_in_country
from cv_writer.profile import load_profile

FIXTURES = Path(__file__).parent.parent.parent / "unit" / "profile" / "fixtures"


def test_load_profile_into_db_populates_identity_histories_bullets_skills(tmp_path):
    profile = load_profile(FIXTURES / "valid_profile.yaml")
    conn = connect(tmp_path / "cv_writer.sqlite3")

    load_profile_into_db(profile, conn)

    identity_row = conn.execute("SELECT name, email FROM identity").fetchone()
    assert identity_row["name"] == "Ana Example"
    assert identity_row["email"] == "ana@example.com"

    history_count = conn.execute("SELECT COUNT(*) AS n FROM job_histories").fetchone()["n"]
    assert history_count == len(profile.job_histories)

    bullet_count = conn.execute("SELECT COUNT(*) AS n FROM bullets").fetchone()["n"]
    assert bullet_count == sum(len(h.bullets) for h in profile.job_histories)

    skill_count = conn.execute("SELECT COUNT(*) AS n FROM skills").fetchone()["n"]
    assert skill_count == len(profile.skills)


def test_reloading_the_same_profile_is_idempotent_no_duplicate_rows(tmp_path):
    profile = load_profile(FIXTURES / "valid_profile.yaml")
    conn = connect(tmp_path / "cv_writer.sqlite3")

    load_profile_into_db(profile, conn)
    load_profile_into_db(profile, conn)
    load_profile_into_db(profile, conn)

    assert conn.execute("SELECT COUNT(*) AS n FROM identity").fetchone()["n"] == 1
    assert conn.execute("SELECT COUNT(*) AS n FROM job_histories").fetchone()["n"] == len(
        profile.job_histories
    )
    assert conn.execute("SELECT COUNT(*) AS n FROM bullets").fetchone()["n"] == sum(
        len(h.bullets) for h in profile.job_histories
    )
    assert conn.execute("SELECT COUNT(*) AS n FROM skills").fetchone()["n"] == len(profile.skills)


def test_db_copy_is_derived_and_rebuildable_reflects_latest_profile_state(tmp_path):
    """Re-running the load after the source profile changes replaces the DB's contents — the
    DB is a rebuildable projection of profile.yaml, not an independently-editable store
    (spec open question 3: YAML is the only write path)."""
    profile = load_profile(FIXTURES / "valid_profile.yaml")
    conn = connect(tmp_path / "cv_writer.sqlite3")
    load_profile_into_db(profile, conn)
    assert conn.execute("SELECT COUNT(*) AS n FROM skills").fetchone()["n"] == 2

    other_profile = load_profile(FIXTURES / "single_quantified_bullet.yaml")
    load_profile_into_db(other_profile, conn)

    assert conn.execute("SELECT COUNT(*) AS n FROM job_histories").fetchone()["n"] == 1
    assert conn.execute("SELECT COUNT(*) AS n FROM skills").fetchone()["n"] == 0


def test_bullets_evidencing_a_skill_can_be_queried_across_histories(tmp_path):
    profile = load_profile(FIXTURES / "valid_profile.yaml")
    conn = connect(tmp_path / "cv_writer.sqlite3")
    load_profile_into_db(profile, conn)

    python_skill = next(s for s in profile.skills if s.name == "Python")
    expected = sum(len(h.bullets) for h in profile.job_histories if h.id in python_skill.evidence)

    rows = bullets_evidencing_skill(conn, "Python")

    assert len(rows) == expected
    assert {row["job_history_id"] for row in rows} == set(python_skill.evidence)


def test_bullets_evidencing_an_unknown_skill_is_an_empty_result(tmp_path):
    profile = load_profile(FIXTURES / "valid_profile.yaml")
    conn = connect(tmp_path / "cv_writer.sqlite3")
    load_profile_into_db(profile, conn)

    assert bullets_evidencing_skill(conn, "Rust") == []


def test_histories_in_a_country_can_be_queried(tmp_path):
    profile = load_profile(FIXTURES / "valid_profile.yaml")
    conn = connect(tmp_path / "cv_writer.sqlite3")
    load_profile_into_db(profile, conn)

    rows = histories_in_country(conn, "Portugal")

    assert {row["id"] for row in rows} == {h.id for h in profile.job_histories}
