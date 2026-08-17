"""Criteria 7, 9 (tier 1), 11: plain HTTP fetch + main-text extraction, with a stubbed HTTP
layer (per the criterion-placement table — tier 1 never touches the network in tests)."""

import pytest

from cv_writer.ingestion.fetch_tier1 import (
    HttpError,
    HttpResponse,
    default_http_get,
    fetch_tier1,
)

POSTING_HTML = """
<html><body>
<nav>skip me</nav>
<h1>Backend Engineer</h1>
<p>""" + ("We build reliable, well-tested backend systems in Python. " * 6) + """</p>
</body></html>
"""


def test_fetch_tier1_extracts_main_text_on_200():
    def stub_http_get(url: str, timeout: float) -> HttpResponse:
        assert url == "https://jobs.example.com/posting/42"
        return HttpResponse(status_code=200, body=POSTING_HTML)

    result = fetch_tier1("https://jobs.example.com/posting/42", http_get=stub_http_get)

    assert result.ok is True
    assert result.status_code == 200
    assert "Backend Engineer" in result.extracted_text
    assert "skip me" not in result.extracted_text


def test_fetch_tier1_fails_on_non_200_status():
    def stub_http_get(url: str, timeout: float) -> HttpResponse:
        return HttpResponse(status_code=404, body="<html>not found</html>")

    result = fetch_tier1("https://jobs.example.com/gone", http_get=stub_http_get)

    assert result.ok is False
    assert result.status_code == 404
    assert "404" in result.reason


def test_fetch_tier1_fails_when_the_request_never_completes():
    def stub_http_get(url: str, timeout: float) -> HttpResponse:
        raise HttpError("connection refused")

    result = fetch_tier1("https://unreachable.example.com", http_get=stub_http_get)

    assert result.ok is False
    assert result.status_code is None
    assert "request failed" in result.reason


def test_fetch_tier1_fails_when_extracted_text_is_below_the_minimum():
    def stub_http_get(url: str, timeout: float) -> HttpResponse:
        return HttpResponse(status_code=200, body="<html><body><div id='root'></div></body></html>")

    result = fetch_tier1(
        "https://spa.example.com/posting", http_get=stub_http_get, min_chars=200
    )

    assert result.ok is False
    assert result.status_code == 200
    assert "minimum 200" in result.reason


@pytest.mark.parametrize("min_chars", [1, 10])
def test_fetch_tier1_succeeds_when_text_meets_a_lower_configured_minimum(min_chars):
    def stub_http_get(url: str, timeout: float) -> HttpResponse:
        return HttpResponse(status_code=200, body="<body><p>short posting</p></body>")

    result = fetch_tier1("https://x.example.com", http_get=stub_http_get, min_chars=min_chars)

    assert result.ok is True


def test_fetch_tier1_never_reports_ok_with_fully_empty_text_even_at_min_chars_zero():
    # Regression: Posting.raw_text requires at least 1 char (models.py); a caller-supplied
    # min_chars of 0 must not let a fully empty extraction through as "ok", which would build
    # an invalid Posting downstream instead of failing cleanly here.
    def stub_http_get(url: str, timeout: float) -> HttpResponse:
        return HttpResponse(status_code=200, body="<html><body></body></html>")

    result = fetch_tier1("https://x.example.com", http_get=stub_http_get, min_chars=0)

    assert result.ok is False


def test_default_http_get_reports_a_malformed_url_as_httperror_not_a_crash():
    # Regression: urllib.request.Request(url, ...) itself can raise ValueError for a
    # scheme-less/malformed URL — must come back as HttpError like every other way the request
    # can fail to complete, not as an uncaught exception.
    with pytest.raises(HttpError):
        default_http_get("jobs.example.com/no-scheme", timeout=5.0)
