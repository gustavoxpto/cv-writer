"""Closes the loop db/track_record.py's own docstring points at: build_application()'s
output really does insert cleanly into a real SQLite track record via the existing
insert_application() — generation stays DB-agnostic (no I/O in generation/ itself), but its
output is exactly what the caller needs to persist without any translation."""

from datetime import date, datetime, timezone

from cv_writer.db import connect, insert_application, list_applications
from cv_writer.generation.build_application import build_application
from cv_writer.generation.models import GeneratedBulletDraft, GeneratedCv
from cv_writer.generation.output_paths import build_output_paths
from cv_writer.ingestion.models import Posting


def test_build_application_output_persists_via_insert_application(tmp_path):
    generated_cv = GeneratedCv(
        markdown="- Cut latency by 77%.",
        language="english",
        variant=None,
        source_ids_used=["job-acme-b1"],
        accepted_bullets=[
            GeneratedBulletDraft(text="Cut latency by 77%.", source_id="job-acme-b1")
        ],
    )
    posting = Posting(
        raw_text="We are hiring.",
        source="https://example.com/job",
        fetched_at=datetime.now(timezone.utc),
        ingestion_tier=1,
    )
    output_paths = build_output_paths(
        date(2026, 1, 10), "Acme Corp", "Backend Engineer", output_dir=tmp_path / "applications"
    )

    application = build_application(
        generated_cv=generated_cv,
        posting=posting,
        company="Acme Corp",
        country="Portugal",
        area="Engineering",
        role_title="Backend Engineer",
        output_paths=output_paths,
        application_date=date(2026, 1, 10),
        match_score=0.9,
        page_count=1,
        skills_featured=["Python"],
    )

    conn = connect(tmp_path / "cv.sqlite3")
    insert_application(conn, application)

    [listed] = list_applications(conn)
    assert listed.company == "Acme Corp"
    assert listed.profile_bullet_ids == ["job-acme-b1"]
    assert listed.markdown_path is not None and listed.markdown_path.endswith(".md")
