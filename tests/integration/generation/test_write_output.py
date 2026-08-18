"""Criteria 25-28 (ADR 0005 decision 6): write_artifacts() with the real render_pdf() — real
Chromium, same posture as tests/integration/generation/test_pdf_render.py. Confirms the PDF's
extracted text matches the Markdown source's content, and that all three files actually land on
disk at the paths build_output_paths() computed.
"""

from datetime import date

from cv_writer.generation.models import GeneratedBulletDraft, GeneratedCv
from cv_writer.generation.output_paths import build_output_paths
from cv_writer.generation.pdf_inspect import extract_text
from cv_writer.generation.write_output import write_artifacts
from cv_writer.profile.models import Identity, Profile


def test_write_artifacts_pdf_extracted_text_matches_the_markdown_source(tmp_path):
    profile = Profile(identity=Identity(name="Ana Example", email="ana@example.com"))
    cv = GeneratedCv(
        markdown="- Cut checkout p99 latency by 77%, from 1.4s to 320ms.",
        language="english",
        variant=None,
        source_ids_used=["job-acme-b1"],
        accepted_bullets=[
            GeneratedBulletDraft(
                text="Cut checkout p99 latency by 77%, from 1.4s to 320ms.",
                source_id="job-acme-b1",
            )
        ],
    )
    paths = build_output_paths(
        date(2026, 1, 10), "Acme Corp", "Backend Engineer", output_dir=tmp_path
    )

    written = write_artifacts(cv=cv, profile=profile, paths=paths)

    assert written.markdown_path.exists()
    assert written.text_path.exists()
    assert written.pdf_path.exists()

    extracted = extract_text(written.pdf_path)
    assert "Ana Example" in extracted
    assert "Cut checkout p99 latency by 77%" in extracted
