"""Criteria 25, 27, 28 (ADR 0005 decision 6): write_artifacts() writes the three generated CV
files (Markdown, plain text, PDF) to the paths build_output_paths() already computed, using an
injected render_pdf_fn so this test runs with no Chromium involved. The real Chromium-backed
path (and the "extracted PDF text matches the Markdown source" assertion) is exercised in
tests/integration/generation/test_write_output.py.
"""

from datetime import date

from cv_writer.generation.models import GeneratedBulletDraft, GeneratedCv
from cv_writer.generation.output_paths import build_output_paths
from cv_writer.generation.write_output import write_artifacts
from cv_writer.profile.models import Identity, Profile


def _profile() -> Profile:
    return Profile(identity=Identity(name="Ana Example", email="ana@example.com"))


def _cv() -> GeneratedCv:
    return GeneratedCv(
        markdown="- Cut latency by 77%.",
        language="english",
        variant=None,
        source_ids_used=["job-acme-b1"],
        accepted_bullets=[
            GeneratedBulletDraft(text="Cut latency by 77%.", source_id="job-acme-b1")
        ],
    )


def _fake_render_pdf(html, output_path):
    # A stand-in for render_pdf() that never touches Chromium — writes a stub file so
    # write_artifacts() has something real to report as written.
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(f"<pdf-stub>{len(html)} bytes of html</pdf-stub>", encoding="utf-8")
    return output_path


def _paths(tmp_path):
    return build_output_paths(
        date(2026, 1, 10), "Acme Corp", "Backend Engineer", output_dir=tmp_path
    )


def test_write_artifacts_writes_all_three_files_to_the_given_paths(tmp_path):
    written = write_artifacts(
        cv=_cv(), profile=_profile(), paths=_paths(tmp_path), render_pdf_fn=_fake_render_pdf
    )

    assert written.markdown_path.exists()
    assert written.pdf_path.exists()
    assert written.text_path.exists()


def test_write_artifacts_markdown_file_contains_the_rendered_markdown_content(tmp_path):
    written = write_artifacts(
        cv=_cv(), profile=_profile(), paths=_paths(tmp_path), render_pdf_fn=_fake_render_pdf
    )

    content = written.markdown_path.read_text(encoding="utf-8")

    assert "Ana Example" in content
    assert "Cut latency by 77%." in content


def test_write_artifacts_text_file_has_markdown_syntax_stripped(tmp_path):
    written = write_artifacts(
        cv=_cv(), profile=_profile(), paths=_paths(tmp_path), render_pdf_fn=_fake_render_pdf
    )

    content = written.text_path.read_text(encoding="utf-8")

    assert "#" not in content
    assert "- Cut latency" not in content
    assert "Cut latency by 77%." in content


def test_write_artifacts_creates_a_missing_output_directory(tmp_path):
    output_dir = tmp_path / "nested" / "applications"
    paths = build_output_paths(
        date(2026, 1, 10), "Acme Corp", "Backend Engineer", output_dir=output_dir
    )

    write_artifacts(cv=_cv(), profile=_profile(), paths=paths, render_pdf_fn=_fake_render_pdf)

    assert output_dir.exists()


def test_write_artifacts_passes_rendered_html_and_the_pdf_path_to_render_pdf_fn(tmp_path):
    paths = _paths(tmp_path)
    captured = {}

    def capturing_render_pdf(html, output_path):
        captured["html"] = html
        captured["output_path"] = output_path
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text("stub", encoding="utf-8")
        return output_path

    write_artifacts(
        cv=_cv(), profile=_profile(), paths=paths, render_pdf_fn=capturing_render_pdf
    )

    assert "<html" in captured["html"].lower()
    assert captured["output_path"] == paths.pdf_path
