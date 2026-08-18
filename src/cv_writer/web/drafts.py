"""ADR 0005 decision 3: in-memory state for one in-progress application ("draft"), keyed by a
uuid4 assigned at creation time.

The `MatchReport` is deliberately not carried on `Draft` — criterion 14 makes it deterministic
and LLM-free, so route handlers re-derive it on every page load from
`extract_requirements()` + `build_match_report()`, both pure functions over the posting text and
the profile. Storing a second copy here would repeat the exact mistake criterion 6 already
forbids for the profile itself (a derived value kept in two places that can drift apart).

Restarting the server loses every in-progress draft — a `DraftStore` is a plain in-memory dict,
nothing here is written to disk. That is a deliberate, documented limitation given this tool's
localhost, single-user, single-session scope (see specs/features/001-cv-writer.md's "Out of
scope"), in the same candid register `generation/output_paths.py`'s own module docstring uses
for its concurrency caveat. Finished applications live in SQLite from the moment
`/drafts/{id}/confirm` succeeds and are entirely unaffected by a restart.
"""

from __future__ import annotations

import uuid

from pydantic import BaseModel, Field

from cv_writer.generation.models import ExtraInput, GeneratedCv
from cv_writer.generation.page_fit import PageFitResult
from cv_writer.ingestion.models import Posting


class Draft(BaseModel):
    """One in-progress application: the ingested posting, the company/country/area/role the
    user confirmed, the extra input accumulated so far, the language choice, and — once
    generation has run — the accepted CV and its page-fit result."""

    id: str
    posting: Posting
    company: str
    country: str
    area: str
    role_title: str
    extra_inputs: list[ExtraInput] = Field(default_factory=list)
    language_override: str | None = None
    generated_cv: GeneratedCv | None = None
    page_fit: PageFitResult | None = None
    page_count: int | None = None


class UnknownDraftError(KeyError):
    """Raised by get()/update() when a draft id doesn't (or no longer) exist — e.g. the server
    restarted since the id was handed out, or the id is simply wrong."""


class DraftStore:
    """A dict of `draft_id -> Draft`. One instance lives on `app.state` per `create_app()` call
    (see web/app.py) rather than as a true module-level global, so each test's app gets its own
    isolated store instead of leaking drafts between tests that each call `create_app()`.
    """

    def __init__(self) -> None:
        self._drafts: dict[str, Draft] = {}

    def create(
        self,
        *,
        posting: Posting,
        company: str,
        country: str,
        area: str,
        role_title: str,
    ) -> Draft:
        draft = Draft(
            id=str(uuid.uuid4()),
            posting=posting,
            company=company,
            country=country,
            area=area,
            role_title=role_title,
        )
        self._drafts[draft.id] = draft
        return draft

    def get(self, draft_id: str) -> Draft:
        try:
            return self._drafts[draft_id]
        except KeyError:
            raise UnknownDraftError(f"no draft with id {draft_id!r}") from None

    def update(self, draft: Draft) -> Draft:
        if draft.id not in self._drafts:
            raise UnknownDraftError(f"no draft with id {draft.id!r}")
        self._drafts[draft.id] = draft
        return draft
