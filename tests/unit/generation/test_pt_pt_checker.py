"""Criterion 21: when the output language resolves to PT-PT, a deterministic, versioned,
data-driven checker flags brasileirismos before the CV is accepted, reporting the offending
line and its PT-PT replacement. Pure function over text — no LLM, no I/O beyond loading the
term list (ADR 0004 decision 6). Written before any generation/LLM code exists, per the spec's
own note that this checker "needs no model to test."
"""

from pathlib import Path

import pytest

from cv_writer.generation.pt_pt_checker import check_pt_pt, load_pt_pt_terms

FIXTURES = Path(__file__).parent / "fixtures"

# The spec's own six named lexis pairs (criterion 21).
LEXIS_PAIRS = [
    ("Trabalho no meu celular todos os dias.", "telemóvel"),
    ("Fiz parte do time de engenharia.", "equipa"),
    ("Guardei o arquivo no servidor.", "ficheiro"),
    ("A tela ficou preta.", "ecrã"),
    ("Preciso gerenciar a equipa.", "gerir"),
    ("O planejamento do projeto foi revisto.", "planeamento"),
]


@pytest.mark.parametrize(("line", "expected_replacement"), LEXIS_PAIRS)
def test_each_spec_named_lexis_pair_is_flagged(line, expected_replacement):
    violations = check_pt_pt(line)

    assert len(violations) == 1
    assert violations[0].line_number == 1
    assert violations[0].line_text == line
    assert violations[0].replacement == expected_replacement


def test_br_progressive_tense_is_flagged_with_pt_pt_replacement_guidance():
    violations = check_pt_pt("Estamos gerenciando o projeto com cuidado.")

    assert len(violations) == 1
    assert "infinitivo" in violations[0].replacement


@pytest.mark.parametrize(
    "line",
    [
        "Construi um pipeline de dados real-time para o processamento de eventos.",
        "Trabalho em regime part-time desde 2022.",
        "Assumi uma posição full-time na equipa de engenharia.",
    ],
)
def test_hyphenated_english_tech_jargon_is_not_flagged_as_the_time_brasileirismo(line):
    # Regression: a plain "time" entry flagged these hyphenated English compounds, since
    # word_boundary_pattern treats a hyphen as a word boundary too (data/pt_pt_terms.yaml's
    # time-equipa entry is now a regex excluding an immediately adjacent hyphen).
    violations = check_pt_pt(line)

    assert violations == []


def test_clean_pt_pt_text_returns_no_violations():
    violations = check_pt_pt(
        "Estou a gerir a equipa e a rever o ficheiro no ecrã do telemóvel."
    )

    assert violations == []


def test_violations_name_the_offending_line_number_in_multiline_text():
    text = "Linha limpa em português.\nUso o celular no trabalho.\nOutra linha limpa."

    violations = check_pt_pt(text)

    assert len(violations) == 1
    assert violations[0].line_number == 2
    assert violations[0].line_text == "Uso o celular no trabalho."


def test_load_pt_pt_terms_picks_up_a_custom_fixture_entry():
    terms = load_pt_pt_terms(FIXTURES / "pt_pt_terms_custom.yaml")

    violations = check_pt_pt("Isto usa uma palavra customizada.", terms=terms)

    assert len(violations) == 1
    assert violations[0].term_id == "custom-entry"


def test_term_list_version_is_present_and_an_int():
    terms = load_pt_pt_terms()

    assert isinstance(terms.version, int)
