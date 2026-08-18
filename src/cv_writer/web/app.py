"""ADR 0005 decision 4: `create_app()` is a factory taking its collaborators by injection —
the profile path, DB path, output directory, the Rephraser, and the URL-ingestion callable are
all overridable. The whole UI runs offline with `FakeRephraser()` and a stub `ingest_url`, no
API key, no network — the same dependency-injection posture the rest of this codebase already
uses everywhere else (there is not one `MagicMock`/`patch` in this repo).
"""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

from fastapi import FastAPI

from cv_writer.db.connection import get_db_path
from cv_writer.generation.output_paths import DEFAULT_OUTPUT_DIR
from cv_writer.generation.rephraser import ClaudeRephraser, Rephraser
from cv_writer.ingestion.models import IngestionFailure, Posting
from cv_writer.ingestion.pipeline import ingest_from_url

from . import routes
from .drafts import DraftStore

DEFAULT_PROFILE_PATH = Path("data") / "profile.yaml"


def create_app(
    *,
    profile_path: Path | None = None,
    db_path: Path | None = None,
    output_dir: Path | None = None,
    rephraser: Rephraser | None = None,
    ingest_url: Callable[..., Posting | IngestionFailure] = ingest_from_url,
) -> FastAPI:
    """Build the FastAPI application. No CORS middleware, no auth middleware, no session
    cookie — criterion 35's localhost-single-user scope is served by never adding half an auth
    story, not by an option to turn one on (see web/__main__.py's DEFAULT_HOST for the binding
    half of that same decision)."""
    app = FastAPI(title="CV Writer")

    app.state.profile_path = profile_path if profile_path is not None else DEFAULT_PROFILE_PATH
    app.state.db_path = db_path if db_path is not None else get_db_path()
    app.state.output_dir = output_dir if output_dir is not None else DEFAULT_OUTPUT_DIR
    app.state.rephraser = rephraser if rephraser is not None else ClaudeRephraser()
    app.state.ingest_url = ingest_url
    app.state.draft_store = DraftStore()

    app.include_router(routes.router)
    return app
