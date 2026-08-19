"""ADR 0005 decision 8 (criterion 35): run the UI with `python -m cv_writer.web`. Binds to
localhost by default — `DEFAULT_HOST` is a module constant, not a `--host` CLI flag, on purpose:
a flag is an invitation, and the spec's "must not be exposed publicly in this version" is better
served by making exposure an edit than an option. No authentication, no session cookie, no CORS
middleware (see web/app.py's create_app()) — this tool is single-user, localhost-only.

`load_dotenv()` runs first so a gitignored `.env` (copied from `.env.example`) supplies
ANTHROPIC_API_KEY automatically — no more exporting it by hand every session. It only ever
populates `os.environ`; the key is still read from the environment at call time by
`ClaudeRephraser` (criterion 23), never stored or passed any other way.
"""

from __future__ import annotations

import uvicorn
from dotenv import load_dotenv

from .app import create_app

DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 8000


def main() -> None:
    load_dotenv()
    uvicorn.run(create_app(), host=DEFAULT_HOST, port=DEFAULT_PORT, reload=False)


if __name__ == "__main__":
    main()
