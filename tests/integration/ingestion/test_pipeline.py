"""Criteria 9, 11: tier escalation (1 -> 2), the tier used is recorded on the Posting, and
ingestion never silently proceeds with thin text — a failure always names what happened and
which tier(s) were tried, so the caller can offer the paste fallback (criterion 9.3) with a
real reason. Tier 2 is stubbed here (its own real-browser behaviour is covered by
test_fetch_tier2.py) so these tests stay about escalation *policy*, not rendering."""

from cv_writer.ingestion.fetch_tier1 import HttpResponse
from cv_writer.ingestion.fetch_tier2 import Tier2Result
from cv_writer.ingestion.models import IngestionFailure, Posting
from cv_writer.ingestion.pipeline import ingest_from_url

GOOD_HTML = "<body><p>" + ("Great Python opportunity at Acme. " * 10) + "</p></body>"


def test_ingest_from_url_uses_tier1_when_it_succeeds():
    def stub_http_get(url, timeout):
        return HttpResponse(status_code=200, body=GOOD_HTML)

    def tier2_should_not_be_called(url, **kwargs):
        raise AssertionError("tier 2 must not run when tier 1 already succeeded")

    result = ingest_from_url(
        "https://jobs.example.com/1",
        http_get=stub_http_get,
        tier2_fetcher=tier2_should_not_be_called,
    )

    assert isinstance(result, Posting)
    assert result.ingestion_tier == 1
    assert result.source == "https://jobs.example.com/1"


def test_ingest_from_url_escalates_to_tier2_when_tier1_fails():
    def stub_http_get(url, timeout):
        return HttpResponse(status_code=503, body="")

    calls = []

    def stub_tier2(url, **kwargs):
        calls.append(url)
        return Tier2Result(ok=True, extracted_text="Great Python opportunity at Acme " * 10)

    result = ingest_from_url(
        "https://jobs.example.com/2", http_get=stub_http_get, tier2_fetcher=stub_tier2
    )

    assert isinstance(result, Posting)
    assert result.ingestion_tier == 2
    assert calls == ["https://jobs.example.com/2"]


def test_ingest_from_url_reports_failure_with_both_tier_reasons_when_both_fail():
    def stub_http_get(url, timeout):
        return HttpResponse(status_code=404, body="")

    def stub_tier2(url, **kwargs):
        return Tier2Result(ok=False, extracted_text="", reason="blocked: HTTP 403")

    result = ingest_from_url(
        "https://jobs.example.com/3", http_get=stub_http_get, tier2_fetcher=stub_tier2
    )

    assert isinstance(result, IngestionFailure)
    assert result.tier_attempted == 2
    assert "404" in result.reason
    assert "403" in result.reason


def test_ingest_from_url_never_returns_a_posting_with_thin_text():
    def stub_http_get(url, timeout):
        return HttpResponse(status_code=200, body="<body><p>hi</p></body>")

    def stub_tier2(url, **kwargs):
        return Tier2Result(ok=False, extracted_text="hi", reason="extracted only 2 chars")

    result = ingest_from_url(
        "https://jobs.example.com/4", http_get=stub_http_get, tier2_fetcher=stub_tier2
    )

    assert isinstance(result, IngestionFailure)


def test_ingest_from_url_recovers_via_tier2_from_malformed_tier1_markup():
    # text_extraction.py's stdlib parser has no HTML5 error recovery: a boilerplate tag that's
    # never properly closed anywhere in malformed markup suppresses the rest of the page for
    # tier 1 (see test_text_extraction.py's test documenting that limitation directly). This
    # proves the escalation pipeline's safety net actually works for that case: tier 1 comes
    # back too thin, tier 2 (here stubbed as "a real browser would parse this fine") recovers.
    malformed_html = "<nav>menu</div><h1>Senior Backend Engineer</h1><p>" + (
        "Requirements: Python and SQL. " * 10
    ) + "</p>"

    def stub_http_get(url, timeout):
        return HttpResponse(status_code=200, body=malformed_html)

    def stub_tier2(url, **kwargs):
        return Tier2Result(ok=True, extracted_text="Senior Backend Engineer " * 20)

    result = ingest_from_url(
        "https://jobs.example.com/5", http_get=stub_http_get, tier2_fetcher=stub_tier2
    )

    assert isinstance(result, Posting)
    assert result.ingestion_tier == 2


def test_ingest_from_url_does_not_crash_on_a_malformed_url():
    from cv_writer.ingestion.fetch_tier1 import HttpError

    def raising_http_get(url, timeout):
        raise HttpError("unknown url type: 'jobs.example.com/42'")

    def stub_tier2(url, **kwargs):
        return Tier2Result(ok=False, extracted_text="", reason="also failed")

    result = ingest_from_url(
        "jobs.example.com/42", http_get=raising_http_get, tier2_fetcher=stub_tier2
    )

    assert isinstance(result, IngestionFailure)
