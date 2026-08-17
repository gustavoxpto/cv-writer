"""Criteria 9 (tier 2), 10, 11: headless-browser render — dismissing a cookie banner, triggering
scroll-lazy content, expanding a "see more" toggle, and refusing to proceed past an explicit
block/CAPTCHA/login-wall response (criterion 10's no-evasion boundary).

Runs against a local fixture HTTP server (never a live site — per the criterion-placement
table and criterion 10 itself: hammering a real site from a test suite would be exactly the
kind of automated traffic criterion 10 rules out).
"""

from __future__ import annotations

import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import pytest

from cv_writer.ingestion.fetch_tier2 import fetch_tier2

FULL_PAGE_HTML = """
<!doctype html>
<html>
<head><title>Job Posting</title></head>
<body>
  <nav>Sitewide navigation chrome</nav>
  <div id="cookie-banner">
    <p>We use cookies.</p>
    <button id="accept-cookies" onclick="
      document.getElementById('cookie-banner').style.display='none';
      document.getElementById('content').style.display='block';
    ">Accept all</button>
  </div>
  <div id="content" style="display:none">
    <h1>Senior Backend Engineer</h1>
    <p>""" + ("We build reliable Python services and value clear communication. " * 5) + """</p>
    <div style="height: 2000px;">(scroll past this to load more)</div>
    <div id="lazy"></div>
    <button id="see-more-btn" onclick="
      document.getElementById('more-text').style.display='block';
      this.style.display='none';
    ">See more</button>
    <div id="more-text" style="display:none">
      Additional responsibilities include on-call rotation and mentoring juniors.
    </div>
  </div>
  <footer>Footer boilerplate</footer>
  <script>
    window.addEventListener('scroll', function () {
      document.getElementById('lazy').innerText =
        'Lazy loaded requirement: Kubernetes experience is a must.';
    });
  </script>
</body>
</html>
"""

CAPTCHA_PAGE_HTML = """
<!doctype html>
<html><body><h1>Please verify you are human before continuing.</h1></body></html>
"""

# The block message lives inside a <header> — one of text_extraction.BOILERPLATE_TAGS. Proves
# the block-signal check runs against the *full* rendered text before boilerplate is stripped.
CAPTCHA_IN_HEADER_HTML = """
<!doctype html>
<html><body><header><h1>Please verify you are human before continuing.</h1></header></body></html>
"""

THIN_PAGE_HTML = "<!doctype html><html><body><p>hi</p></body></html>"

PAGES = {
    "/full": FULL_PAGE_HTML,
    "/captcha": CAPTCHA_PAGE_HTML,
    "/captcha-in-header": CAPTCHA_IN_HEADER_HTML,
    "/thin": THIN_PAGE_HTML,
}


class _FixtureHandler(BaseHTTPRequestHandler):
    def do_GET(self):  # noqa: N802 (stdlib method name)
        if self.path == "/blocked-status":
            self._respond(403, "<html><body>Forbidden</body></html>")
            return
        html = PAGES.get(self.path)
        if html is None:
            self._respond(404, "<html><body>not found</body></html>")
            return
        self._respond(200, html)

    def _respond(self, status: int, body: str) -> None:
        encoded = body.encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(encoded)))
        self.end_headers()
        self.wfile.write(encoded)

    def log_message(self, format, *args):  # noqa: A002 (stdlib signature)
        pass  # keep test output quiet


@pytest.fixture(scope="module")
def fixture_server():
    server = ThreadingHTTPServer(("127.0.0.1", 0), _FixtureHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield f"http://127.0.0.1:{server.server_address[1]}"
    finally:
        server.shutdown()
        thread.join(timeout=5)


def test_fetch_tier2_dismisses_cookie_banner_scrolls_and_expands_see_more(fixture_server):
    result = fetch_tier2(f"{fixture_server}/full", min_chars=50)

    assert result.ok is True, result.reason
    assert "Senior Backend Engineer" in result.extracted_text  # banner was dismissed
    assert "Kubernetes experience is a must" in result.extracted_text  # scroll triggered lazy
    assert "on-call rotation" in result.extracted_text  # see-more expanded
    assert "Sitewide navigation chrome" not in result.extracted_text  # boilerplate stripped
    assert "Footer boilerplate" not in result.extracted_text


def test_fetch_tier2_stops_on_an_explicit_block_status_without_retrying(fixture_server):
    result = fetch_tier2(f"{fixture_server}/blocked-status", min_chars=50)

    assert result.ok is False
    assert "403" in result.reason


def test_fetch_tier2_stops_on_a_captcha_challenge_rather_than_solving_it(fixture_server):
    result = fetch_tier2(f"{fixture_server}/captcha", min_chars=50)

    assert result.ok is False
    assert "verify you are human" in result.reason.lower()


def test_fetch_tier2_detects_a_block_message_rendered_inside_a_boilerplate_tag(fixture_server):
    # Regression: the block-signal check must run before boilerplate (incl. <header>) is
    # stripped from the DOM, or a block message rendered inside one is silently discarded.
    result = fetch_tier2(f"{fixture_server}/captcha-in-header", min_chars=50)

    assert result.ok is False
    assert "verify you are human" in result.reason.lower()


def test_fetch_tier2_fails_on_any_non_200_status_not_just_the_named_block_codes(fixture_server):
    # Regression: a 404 (or any other non-200 not in the explicit block-code set) must not
    # fall through to full rendering — tier 2 should refuse a dead-page response the same way
    # tier 1 refuses any non-200, rather than returning that page's boilerplate-stripped filler
    # text as if it were real posting content.
    result = fetch_tier2(f"{fixture_server}/does-not-exist", min_chars=5)

    assert result.ok is False
    assert "404" in result.reason


def test_fetch_tier2_reports_thin_pages_instead_of_proceeding_silently(fixture_server):
    result = fetch_tier2(f"{fixture_server}/thin", min_chars=200)

    assert result.ok is False
    assert "minimum 200" in result.reason
