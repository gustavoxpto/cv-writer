"""ADR 0005 decision 8 (criterion 35): the UI binds to localhost by default and ships no
authentication, session, or CORS middleware — this version is single-user and must not be
exposed publicly. No web server is started here (criterion 34's "tests for A-F never start a
web server" posture, extended to this UI-shell-config check): DEFAULT_HOST/DEFAULT_PORT are
read as plain constants and create_app()'s installed middleware list is inspected directly.
"""

from __future__ import annotations

from cv_writer.web.__main__ import DEFAULT_HOST, DEFAULT_PORT
from cv_writer.web.app import create_app


def test_default_host_is_loopback_only_not_a_wildcard_bind():
    assert DEFAULT_HOST == "127.0.0.1"


def test_default_port_is_the_documented_local_port():
    assert DEFAULT_PORT == 8000


def test_create_app_installs_no_cors_auth_or_session_middleware():
    app = create_app()

    middleware_class_names = {middleware.cls.__name__.lower() for middleware in app.user_middleware}

    assert not any("cors" in name for name in middleware_class_names)
    assert not any("auth" in name for name in middleware_class_names)
    assert not any("session" in name for name in middleware_class_names)
