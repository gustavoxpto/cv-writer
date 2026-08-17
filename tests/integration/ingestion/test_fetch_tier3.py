"""Criterion 8: a posting can be ingested by pasting raw text, with company/role/country
entered by the user; pasted and fetched postings are otherwise indistinguishable downstream."""

import pytest

from cv_writer.ingestion.fetch_tier3 import ingest_pasted
from cv_writer.ingestion.models import PASTED_SOURCE


def test_ingest_pasted_builds_a_posting_from_the_given_fields():
    posting = ingest_pasted(
        "  We are hiring a Backend Engineer.  ",
        company="Acme Corp",
        role_title="Backend Engineer",
        country="Portugal",
    )

    assert posting.raw_text == "We are hiring a Backend Engineer."
    assert posting.source == PASTED_SOURCE
    assert posting.ingestion_tier == 3
    assert posting.company == "Acme Corp"
    assert posting.role_title == "Backend Engineer"
    assert posting.country == "Portugal"
    assert posting.fetched_at is not None


def test_ingest_pasted_rejects_empty_text():
    with pytest.raises(ValueError, match="empty"):
        ingest_pasted("   ", company="Acme Corp", role_title="Engineer", country="Portugal")


@pytest.mark.parametrize(
    "kwargs",
    [
        {"company": "  ", "role_title": "Engineer", "country": "Portugal"},
        {"company": "Acme Corp", "role_title": "  ", "country": "Portugal"},
        {"company": "Acme Corp", "role_title": "Engineer", "country": "  "},
    ],
)
def test_ingest_pasted_rejects_blank_identifying_fields(kwargs):
    with pytest.raises(ValueError):
        ingest_pasted("We are hiring.", **kwargs)
