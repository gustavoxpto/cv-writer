"""build_application() is a pure mapper from a successful generation result into
db.track_record.Application — no DB I/O in generation/ at all (see that module's docstring
and ADR 0004's "generation stays DB-agnostic" framing). The caller — an integration test
today, slice 5's UI later — is the one that calls the existing insert_application()."""

from datetime import date, datetime, timezone

from cv_writer.db import Application
from cv_writer.generation.build_application import build_application
from cv_writer.generation.models import GeneratedBulletDraft, GeneratedCv
from cv_writer.generation.output_paths import OutputPaths
from cv_writer.ingestion.models import Posting


def test_build_application_maps_a_generated_cv_into_an_application():
    generated_cv = GeneratedCv(
        markdown="- Cut latency by 77%.",
        language="english",
        variant=None,
        source_ids_used=["job-acme-b1", "extra-1"],
        accepted_bullets=[
            GeneratedBulletDraft(text="Cut latency by 77%.", source_id="job-acme-b1"),
        ],
    )
    posting = Posting(
        raw_text="We are hiring.",
        source="https://example.com/job",
        fetched_at=datetime.now(timezone.utc),
        ingestion_tier=1,
    )
    output_paths = OutputPaths(
        markdown_path=("data/applications/2026-01-10-acme-corp-backend-engineer.md"),
        pdf_path=("data/applications/2026-01-10-acme-corp-backend-engineer.pdf"),
        text_path=("data/applications/2026-01-10-acme-corp-backend-engineer.txt"),
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
        match_score=0.82,
        page_count=1,
        skills_featured=["Python"],
    )

    assert isinstance(application, Application)
    assert application.company == "Acme Corp"
    assert application.source == "https://example.com/job"
    assert application.ingestion_tier == 1
    assert application.output_language == "english"
    assert application.page_count == 1
    assert application.match_score == 0.82
    assert application.skills_featured == ["Python"]
    assert application.profile_bullet_ids == ["job-acme-b1", "extra-1"]
    assert str(application.markdown_path).endswith(".md")


def test_build_application_uses_the_pt_variant_as_output_language_when_present():
    generated_cv = GeneratedCv(
        markdown="- Geri a equipa.",
        language="portuguese",
        variant="pt-pt",
        source_ids_used=["job-acme-b1"],
        accepted_bullets=[GeneratedBulletDraft(text="Geri a equipa.", source_id="job-acme-b1")],
    )
    posting = Posting(
        raw_text="Vaga.",
        source="pasted",
        fetched_at=datetime.now(timezone.utc),
        ingestion_tier=3,
    )
    output_paths = OutputPaths(
        markdown_path=("data/applications/x.md"),
        pdf_path=("data/applications/x.pdf"),
        text_path=("data/applications/x.txt"),
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
        match_score=None,
        page_count=2,
        skills_featured=[],
    )

    assert application.output_language == "pt-pt"
    assert application.source == "pasted"
