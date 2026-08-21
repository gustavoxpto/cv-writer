"""Spec 002 AC-003: a posting's own section headings decide required vs preferred, in Spanish
and Portuguese as well as English.

The extractor splits posting text into a "required" zone and a "preferred" zone by scanning for
section markers, defaulting to required until a preferred marker appears. Until spec 002 those
markers were English-only, so a Spanish posting's entire body counted as required — and a
"nice to have" skill was reported as a hard requirement, or the section was not recognised at
all. These tests assert the zone actually flips, and — the half that matters — that a preferred
skill is *not* also reported as required.
"""

from __future__ import annotations

from cv_writer.ingestion.models import RequirementKind
from cv_writer.ingestion.requirements import extract_requirements

# Deliberately minimal postings: each skill appears exactly once, under exactly one heading.
# The extractor keeps the first match of a phrase, so a skill mentioned in both zones would make
# these tests prove nothing about zoning.
#
# The preferred heading comes FIRST in these fixtures, which reads oddly for a job ad and is the
# whole point. "Required" is the extractor's default zone, so a skill under a required heading in
# an otherwise unmarked posting is reported as required whether or not the heading was recognised
# — a test written in the natural order would pass with "requisitos" absent from the term file
# and prove nothing. Putting a preferred heading above it means the required heading has to
# actually be recognised to flip the zone back.
SPANISH_POSTING = """
Consultor de Formación

Sobre el puesto:
Buscarás mejorar los procesos de aprendizaje del equipo.

Se valorará:
- Conocimientos de consultoría estratégica
- Experiencia con entorno google

Requisitos:
- Experiencia en gestión de proyectos
- Dominio del paquete office
"""

PORTUGUESE_POSTING = """
Consultor de Formação

Sobre a vaga:
Vais apoiar as equipas na melhoria dos processos de aprendizagem.

Diferenciais:
- Conhecimentos de consultoría estratégica
- Experiência com entorno google

Requisitos:
- Experiência em gestión de proyectos
- Domínio do paquete office
"""


def _by_kind(text: str, kind: RequirementKind) -> set[str]:
    return {r.value for r in extract_requirements(text).of_kind(kind)}


def test_spanish_requisitos_heading_marks_skills_as_required():
    """AC-003: "Requisitos:" opens a required zone, as "Requirements:" already did. Discriminating
    because a preferred heading sits above it — without the marker these two skills would be
    reported as preferred."""
    required = _by_kind(SPANISH_POSTING, RequirementKind.REQUIRED_SKILL)

    assert "project planning" in required
    assert "microsoft office" in required


def test_spanish_se_valorara_heading_marks_skills_as_preferred_only():
    """AC-003: "Se valorará" ("will be valued") opens a preferred zone. The second assertion is
    the one with teeth — a skill leaking into both zones would satisfy the first alone."""
    preferred = _by_kind(SPANISH_POSTING, RequirementKind.PREFERRED_SKILL)
    required = _by_kind(SPANISH_POSTING, RequirementKind.REQUIRED_SKILL)

    assert "strategic consulting" in preferred
    assert "google workspace" in preferred
    assert "strategic consulting" not in required
    assert "google workspace" not in required


def test_portuguese_requisitos_heading_marks_skills_as_required():
    """AC-003: the Portuguese required heading is spelled the same as the Spanish one. Same
    preferred-heading-above arrangement, for the same discriminating reason."""
    required = _by_kind(PORTUGUESE_POSTING, RequirementKind.REQUIRED_SKILL)

    assert "project planning" in required
    assert "microsoft office" in required


def test_portuguese_diferenciais_heading_marks_skills_as_preferred_only():
    """AC-003: "Diferenciais" is the Portuguese-language equivalent of "nice to have"."""
    preferred = _by_kind(PORTUGUESE_POSTING, RequirementKind.PREFERRED_SKILL)
    required = _by_kind(PORTUGUESE_POSTING, RequirementKind.REQUIRED_SKILL)

    assert "strategic consulting" in preferred
    assert "google workspace" in preferred
    assert "strategic consulting" not in required
    assert "google workspace" not in required


def test_a_posting_with_no_recognised_heading_still_defaults_to_required():
    """Regression guard on the pre-existing default: adding markers must not change what happens
    when none of them appear. A posting with no headings is all required, not all preferred."""
    unstructured = "Buscamos un consultor con experiencia en consultoría estratégica."

    result = extract_requirements(unstructured)

    assert "strategic consulting" in {
        r.value for r in result.of_kind(RequirementKind.REQUIRED_SKILL)
    }
    assert result.of_kind(RequirementKind.PREFERRED_SKILL) == []
