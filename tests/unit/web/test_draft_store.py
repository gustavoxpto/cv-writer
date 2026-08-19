"""ADR 0005 decision 3: DraftStore is a plain in-memory dict of draft_id -> Draft, keyed by a
uuid4 assigned at creation time. No I/O, no web server — criterion 34 requires tests for A-F
(and this store, part of the UI shell's own state, follows the same posture) to never start
one; this test drives DraftStore directly.
"""

from __future__ import annotations

from datetime import datetime, timezone

import pytest

from cv_writer.ingestion.models import Posting
from cv_writer.web.drafts import DraftStore, UnknownDraftError


def _posting(source: str = "https://example.com/job") -> Posting:
    return Posting(
        raw_text="We are hiring a backend engineer.",
        source=source,
        fetched_at=datetime.now(timezone.utc),
        ingestion_tier=1,
    )


def _create(store: DraftStore, **overrides):
    fields = {
        "posting": _posting(),
        "company": "Acme Corp",
        "country": "Portugal",
        "area": "Engineering",
        "role_title": "Backend Engineer",
    }
    fields.update(overrides)
    return store.create(**fields)


def test_create_returns_a_draft_holding_the_given_posting_and_confirmed_fields():
    store = DraftStore()

    draft = _create(store)

    assert draft.posting.source == "https://example.com/job"
    assert draft.company == "Acme Corp"
    assert draft.country == "Portugal"
    assert draft.area == "Engineering"
    assert draft.role_title == "Backend Engineer"
    assert draft.extra_inputs == []
    assert draft.generated_cv is None


def test_create_assigns_a_non_empty_id():
    store = DraftStore()

    draft = _create(store)

    assert draft.id


def test_get_returns_the_same_draft_that_was_created():
    store = DraftStore()
    created = _create(store)

    fetched = store.get(created.id)

    assert fetched == created


def test_get_raises_unknown_draft_error_for_an_id_that_was_never_created():
    store = DraftStore()

    with pytest.raises(UnknownDraftError):
        store.get("does-not-exist")


def test_two_created_drafts_are_assigned_different_ids():
    store = DraftStore()

    first = _create(store)
    second = _create(store, company="Globex")

    assert first.id != second.id


def test_update_persists_changes_visible_to_a_later_get():
    store = DraftStore()
    draft = _create(store)
    draft.language_override = "english"

    store.update(draft)

    assert store.get(draft.id).language_override == "english"


def test_update_raises_unknown_draft_error_for_a_draft_id_never_created():
    store = DraftStore()
    draft = _create(store)
    draft.id = "some-other-id-never-created"

    with pytest.raises(UnknownDraftError):
        store.update(draft)
