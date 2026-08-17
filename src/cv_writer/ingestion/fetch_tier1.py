"""Tier 1 ingestion: plain HTTP GET + main-text extraction (criterion 7; tier 1 of criterion 9).

`http_get` is injectable so tests never touch the network (per the criterion-placement table:
"tier 1 with a stubbed HTTP layer"); `default_http_get` is the real implementation, a thin
`urllib` wrapper (ADR 0003: no new HTTP dependency for one GET request).
"""

from __future__ import annotations

import urllib.error
import urllib.request
from collections.abc import Callable
from dataclasses import dataclass

from .text_extraction import extract_main_text

DEFAULT_TIMEOUT_SECONDS = 10.0
# Below this many extracted characters, tier 1 treats the page as a JS-only shell or otherwise
# too thin to be a real posting, and escalates to tier 2 (criterion 9.1 -> 9.2). Configurable
# per-call since what counts as "too thin" may vary by call site (e.g. tests use a lower bar).
DEFAULT_MIN_EXTRACTED_CHARS = 200
USER_AGENT = "cv-writer/0.1 (+personal job-application tool; one fetch per posting, no retries)"


@dataclass
class HttpResponse:
    status_code: int
    body: str


class HttpError(Exception):
    """The request never completed (DNS failure, connection refused, timeout) — distinct from
    an HttpResponse with a non-200 status, which is a response the server chose to send."""


def default_http_get(url: str, timeout: float) -> HttpResponse:
    try:
        # Request(...) itself parses the URL and can raise ValueError for a malformed or
        # scheme-less one (e.g. "jobs.example.com/42") — kept inside the try so that, like
        # every other way this request can fail to complete, it comes back as HttpError
        # rather than an uncaught exception (criterion 11: never a silent *or* a crashing
        # failure).
        request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
        with urllib.request.urlopen(request, timeout=timeout) as response:  # noqa: S310
            charset = response.headers.get_content_charset() or "utf-8"
            body = response.read().decode(charset, errors="replace")
            return HttpResponse(status_code=response.status, body=body)
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace") if exc.fp else ""
        return HttpResponse(status_code=exc.code, body=body)
    except (urllib.error.URLError, TimeoutError, OSError, ValueError) as exc:
        raise HttpError(str(exc)) from exc


@dataclass
class Tier1Result:
    """Outcome of one tier-1 attempt: usable text, or a reason to escalate to tier 2
    (criterion 9.1 -> 9.2). `status_code` is None when the request never completed at all."""

    ok: bool
    extracted_text: str
    status_code: int | None
    reason: str | None = None


def fetch_tier1(
    url: str,
    *,
    http_get: Callable[[str, float], HttpResponse] = default_http_get,
    timeout: float = DEFAULT_TIMEOUT_SECONDS,
    min_chars: int = DEFAULT_MIN_EXTRACTED_CHARS,
) -> Tier1Result:
    try:
        response = http_get(url, timeout)
    except HttpError as exc:
        return Tier1Result(
            ok=False, extracted_text="", status_code=None, reason=f"request failed: {exc}"
        )

    if response.status_code != 200:
        return Tier1Result(
            ok=False,
            extracted_text="",
            status_code=response.status_code,
            reason=f"non-200 status ({response.status_code})",
        )

    text = extract_main_text(response.body)
    # `max(min_chars, 1)`: Posting.raw_text requires at least 1 character (models.py), so even
    # a caller-supplied min_chars of 0 (or less) must not let a fully empty extraction through
    # as "ok" — that would build an invalid Posting downstream instead of failing cleanly here.
    effective_min_chars = max(min_chars, 1)
    if len(text) < effective_min_chars:
        return Tier1Result(
            ok=False,
            extracted_text=text,
            status_code=response.status_code,
            reason=(
                f"extracted only {len(text)} chars (minimum {min_chars}) — likely a JS-only "
                "shell or a page with little real content"
            ),
        )

    return Tier1Result(ok=True, extracted_text=text, status_code=response.status_code)
