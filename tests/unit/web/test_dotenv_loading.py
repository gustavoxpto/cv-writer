"""ANTHROPIC_API_KEY previously had to be exported by hand every session (docs/handoff-
operational-readiness.md's Blocker 2). main() now loads a gitignored .env automatically via
python-dotenv before the app/server start, so the key just needs to live in .env once.

No real server is started here (same posture as test_localhost_binding.py, criterion 34's
"tests for A-F never start a web server" extended to this entry-point check): load_dotenv and
uvicorn.run are both replaced with fakes that record call order into a shared list, so we can
assert load_dotenv runs before uvicorn.run without ever binding a socket or touching a real
.env file.
"""

from __future__ import annotations

from cv_writer.web import __main__ as web_main


def test_main_loads_dotenv_before_starting_the_server(monkeypatch):
    call_order: list[str] = []

    monkeypatch.setattr(
        web_main, "load_dotenv", lambda: call_order.append("load_dotenv")
    )
    monkeypatch.setattr(
        web_main.uvicorn, "run", lambda *args, **kwargs: call_order.append("uvicorn.run")
    )

    web_main.main()

    assert call_order == ["load_dotenv", "uvicorn.run"]
