"""Tier 2 ingestion: headless-browser render (criterion 9.2), reached only when tier 1 fails.

A *rendering* strategy, not an evasion strategy (criterion 10): one navigation, no retries, no
login attempts, no CAPTCHA solving. It identifies itself honestly with the same custom User-
Agent tier 1 uses — deliberately not a spoofed "real browser" string, since pretending not to
be automated is exactly the kind of evasion criterion 10 rules out. If the page answers with a
block, a login wall, or a CAPTCHA challenge, tier 2 stops immediately and hands back a reason
(criterion 9.3) rather than trying to work around it.

Uses Playwright + Chromium (ADR 0003) — the same browser slice 4 will reuse for PDF rendering.
"""

from __future__ import annotations

from dataclasses import dataclass

from playwright.sync_api import Error as PlaywrightError
from playwright.sync_api import TimeoutError as PlaywrightTimeoutError
from playwright.sync_api import sync_playwright

from .fetch_tier1 import DEFAULT_MIN_EXTRACTED_CHARS, USER_AGENT
from .text_extraction import BOILERPLATE_TAGS, collapse_whitespace

DEFAULT_NAV_TIMEOUT_MS = 15_000
SCROLL_STEPS = 6
SCROLL_PAUSE_MS = 150

# A response at one of these statuses is the site explicitly refusing the request, rather than
# just failing — worth its own "blocked: HTTP xxx" reason. Any *other* non-200 status also
# stops tier 2 (matching tier 1's "any non-200 fails" rule, fetch_tier1.py) rather than letting
# e.g. a branded 404 page's boilerplate-stripped filler text pass as real posting content.
_BLOCK_STATUS_CODES = frozenset({401, 403, 429, 503})

# Visible page text containing any of these (case-insensitive) means a challenge or login wall
# stands between us and the posting — stop, don't attempt to solve or bypass it (criterion 10).
_BLOCK_SIGNAL_PHRASES = (
    "verify you are human",
    "are you a robot",
    "captcha",
    "access denied",
    "please sign in to continue",
    "please log in to continue",
    "log in to see this",
    "sign in to see this",
    "unusual traffic from your",
)

# Standard "accept all" cookie/consent controls, tried in order; the first one present is
# clicked and we stop looking (criterion 9.2: "dismiss cookie/consent banners by their standard
# accept controls").
_COOKIE_ACCEPT_SELECTORS = (
    "#onetrust-accept-btn-handler",
    "button:has-text('Accept all')",
    "button:has-text('Accept All')",
    "button:has-text('Accept all cookies')",
    "button:has-text('Accept cookies')",
    "button:has-text('I accept')",
    "button:has-text('I agree')",
    "button:has-text('Agree')",
    "button:has-text('Got it')",
    "[aria-label='Accept cookies']",
    "[aria-label='Accept all']",
)

# "See more" / "Show more" toggles that hide the rest of a posting's body text.
_EXPAND_SELECTORS = (
    "button:has-text('See more')",
    "button:has-text('Show more')",
    "button:has-text('Read more')",
    "a:has-text('See more')",
    "a:has-text('Show more')",
)


@dataclass
class Tier2Result:
    """Outcome of one tier-2 attempt: usable text, or a reason to hand over to the paste
    fallback (criterion 9.3)."""

    ok: bool
    extracted_text: str
    reason: str | None = None


def fetch_tier2(
    url: str,
    *,
    nav_timeout_ms: int = DEFAULT_NAV_TIMEOUT_MS,
    min_chars: int = DEFAULT_MIN_EXTRACTED_CHARS,
) -> Tier2Result:
    try:
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch()
            try:
                return _render(
                    browser, url, nav_timeout_ms=nav_timeout_ms, min_chars=min_chars
                )
            finally:
                browser.close()
    except PlaywrightError as exc:
        return Tier2Result(ok=False, extracted_text="", reason=f"browser render failed: {exc}")


def _render(browser, url: str, *, nav_timeout_ms: int, min_chars: int) -> Tier2Result:
    page = browser.new_page(user_agent=USER_AGENT)

    try:
        response = page.goto(url, timeout=nav_timeout_ms, wait_until="domcontentloaded")
    except PlaywrightTimeoutError:
        return Tier2Result(ok=False, extracted_text="", reason="page load timed out")

    if response is not None and response.status != 200:
        if response.status in _BLOCK_STATUS_CODES:
            return Tier2Result(
                ok=False, extracted_text="", reason=f"blocked: HTTP {response.status}"
            )
        return Tier2Result(
            ok=False, extracted_text="", reason=f"non-200 status ({response.status})"
        )

    try:
        page.wait_for_load_state("networkidle", timeout=nav_timeout_ms)
    except PlaywrightTimeoutError:
        pass  # some pages never go fully idle (polling widgets, analytics beacons) — proceed

    _dismiss_cookie_banner(page)
    _scroll_to_trigger_lazy_content(page)
    _expand_see_more(page)

    # Check block/CAPTCHA/login-wall signals against the *full* rendered text first — a block
    # message can legitimately render inside a <header> or <aside> wrapper (common for banner-
    # style interstitials), and stripping boilerplate before this check would silently discard
    # the very signal criterion 10 needs to see, wherever on the page it renders.
    full_text = page.inner_text("body")
    lowered = full_text.lower()
    for phrase in _BLOCK_SIGNAL_PHRASES:
        if phrase in lowered:
            return Tier2Result(
                ok=False, extracted_text="", reason=f"blocked: page shows '{phrase}'"
            )

    # Only now remove boilerplate tags from the live DOM (same tag list as tier 1's extractor
    # — see text_extraction.py's module docstring) and re-read, so the final text reflects both
    # "not page chrome" and "actually visible after our interactions" (CSS display:none a raw-
    # HTML parser can't evaluate).
    page.evaluate(
        "(tags) => tags.forEach(t => document.querySelectorAll(t).forEach(el => el.remove()))",
        list(BOILERPLATE_TAGS),
    )
    text = collapse_whitespace(page.inner_text("body"))
    if len(text) < min_chars:
        return Tier2Result(
            ok=False,
            extracted_text=text,
            reason=(
                f"extracted only {len(text)} chars (minimum {min_chars}) after render — "
                "still too thin to be a real posting"
            ),
        )

    return Tier2Result(ok=True, extracted_text=text)


def _dismiss_cookie_banner(page) -> None:
    _click_first_match(page, _COOKIE_ACCEPT_SELECTORS)


def _expand_see_more(page) -> None:
    for selector in _EXPAND_SELECTORS:
        _click_first_match(page, (selector,))


def _click_first_match(page, selectors: tuple[str, ...]) -> None:
    for selector in selectors:
        try:
            locator = page.locator(selector).first
            if locator.count() == 0:
                continue
            locator.click(timeout=1_500)
            page.wait_for_timeout(200)
            return
        except PlaywrightError:
            continue


def _scroll_to_trigger_lazy_content(page) -> None:
    # Deliberately paced, not a tight loop hammering the page (criterion 9.2's "slower and
    # unhurried rather than hammering the site").
    for _ in range(SCROLL_STEPS):
        page.mouse.wheel(0, 2_000)
        page.wait_for_timeout(SCROLL_PAUSE_MS)
