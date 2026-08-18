"""Criterion 28: output paths are deterministic and collision-free per application (date +
company + role slug), and generating twice for the same application produces a new version
rather than overwriting a previous artifact."""

from datetime import date

from cv_writer.generation.output_paths import OutputPaths, build_output_paths

APPLICATION_DATE = date(2026, 1, 10)


def _paths(company: str, role_title: str, tmp_path) -> OutputPaths:
    return build_output_paths(APPLICATION_DATE, company, role_title, output_dir=tmp_path)


def test_paths_are_deterministic_for_the_same_inputs(tmp_path):
    first = _paths("Acme Corp", "Backend Engineer", tmp_path)
    second = _paths("Acme Corp", "Backend Engineer", tmp_path)

    assert first == second


def test_paths_are_slugged_from_date_company_and_role(tmp_path):
    paths = _paths("Acme Corp", "Backend Engineer", tmp_path)

    assert "2026-01-10" in paths.markdown_path.name
    assert "acme-corp" in paths.markdown_path.name
    assert "backend-engineer" in paths.markdown_path.name
    assert paths.markdown_path.suffix == ".md"
    assert paths.pdf_path.suffix == ".pdf"
    assert paths.text_path.suffix == ".txt"


def test_regenerating_for_the_same_application_gets_a_new_version_never_overwrites(tmp_path):
    first = _paths("Acme Corp", "Backend Engineer", tmp_path)
    # Simulate the first generation actually having written a file at that path.
    first.markdown_path.parent.mkdir(parents=True, exist_ok=True)
    first.markdown_path.write_text("v1", encoding="utf-8")

    second = _paths("Acme Corp", "Backend Engineer", tmp_path)

    assert second.markdown_path != first.markdown_path
    assert not second.markdown_path.exists()


def test_different_companies_never_collide(tmp_path):
    acme = _paths("Acme Corp", "Backend Engineer", tmp_path)
    globex = _paths("Globex", "Backend Engineer", tmp_path)

    assert acme.markdown_path != globex.markdown_path
