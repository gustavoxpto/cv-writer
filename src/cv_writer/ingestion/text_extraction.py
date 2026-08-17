"""Extract the main visible text from raw HTML (criterion 7's "extracts the main text").

Deliberately not a full readability algorithm (see ADR 0003): a boilerplate-tag blocklist plus
visible-text concatenation, using only the stdlib `html.parser`. Pure function, no I/O — used
by tier 1, which only ever has raw (unrendered) HTML from `urllib`.

Tier 2 (fetch_tier2.py) shares `BOILERPLATE_TAGS` and `collapse_whitespace` — "boilerplate"
and "how extracted text gets normalized" mean the same thing in both tiers — but not this
parser: after JS interaction, tier 2's HTML also carries CSS visibility (`display:none` on a
still-collapsed panel) that this stdlib parser can't evaluate, so tier 2 removes boilerplate
tags from Playwright's live DOM instead and lets the rendered engine's own visible-text
extraction handle the rest. Same *policy* ("what counts as page chrome", "how whitespace gets
normalized"), different mechanism, because tier 2's input has state this parser can't see.

Known limitation, not fixed here: `html.parser` has no error-recovery for a boilerplate tag
that is opened but never properly closed anywhere in malformed markup (a real browser's HTML5
parser auto-closes such tags per spec; this stdlib parser doesn't). Worst case, that suppresses
the rest of the page's text and `extract_main_text()` returns too little — which is exactly
the "extracts less than the configured minimum" condition fetch_tier1.py already escalates on
(criterion 9.1 -> 9.2), so tier 2's real browser recovers the text tier 1's simpler parser
couldn't. See test_text_extraction.py for a case proving that safety net.
"""

from __future__ import annotations

from html.parser import HTMLParser

# Tags whose contents are never part of "the main text" — page chrome, not content. Shared with
# fetch_tier2.py (see module docstring) so both tiers agree on what "boilerplate" means.
BOILERPLATE_TAGS = frozenset(
    {"script", "style", "nav", "header", "footer", "aside", "form", "noscript", "svg", "button"}
)
# Block-level tags: a line break is inserted around them so words from separate elements never
# collide into one another (e.g. "</li><li>" becoming "itemitem").
_BLOCK_TAGS = frozenset(
    {
        "p", "div", "li", "ul", "ol", "br", "h1", "h2", "h3", "h4", "h5", "h6",
        "section", "article", "tr", "td", "th", "table", "blockquote", "pre",
    }
)


class _MainTextParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        # A stack (not a counter) of currently-open boilerplate tag names: on a mismatched
        # close (some *other* tag closing while a boilerplate tag is still open — common in
        # real-world markup), only the matching entry is popped, so one crossed pair doesn't
        # desync the skip state the way a flat increment/decrement counter would.
        self._skip_stack: list[str] = []
        self._chunks: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag in BOILERPLATE_TAGS:
            self._skip_stack.append(tag)
        elif tag in _BLOCK_TAGS:
            self._chunks.append("\n")

    def handle_startendtag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag in _BLOCK_TAGS:
            self._chunks.append("\n")

    def handle_endtag(self, tag: str) -> None:
        if tag in BOILERPLATE_TAGS and tag in self._skip_stack:
            # Pop the most recent open occurrence of this tag, not necessarily the top of the
            # stack — tolerates one boilerplate tag closing out of order relative to another.
            for i in range(len(self._skip_stack) - 1, -1, -1):
                if self._skip_stack[i] == tag:
                    del self._skip_stack[i]
                    break
        elif tag in _BLOCK_TAGS:
            self._chunks.append("\n")

    def handle_data(self, data: str) -> None:
        if not self._skip_stack and data.strip():
            # Joined with a leading space, not concatenated directly: adjacent inline elements
            # with no whitespace between them in the source (e.g. "<span>Python</span><span>
            # SQL</span>") must not merge into one unmatchable token ("PythonSQL"). A run of
            # extra spaces this introduces (or block-tag "\n" markers landing next to a space)
            # is cleaned up by collapse_whitespace() below.
            self._chunks.append(" " + data)

    @property
    def text(self) -> str:
        return "".join(self._chunks)


def collapse_whitespace(text: str) -> str:
    """Collapse internal whitespace runs to single spaces, strip each line, and drop blank
    lines. Shared by tier 1's extract_main_text() and tier 2's fetch_tier2() so both tiers
    normalize extracted text the same way (see module docstring)."""
    lines = (" ".join(line.split()) for line in text.splitlines())
    return "\n".join(line for line in lines if line)


def extract_main_text(html: str) -> str:
    """Return the visible body text of `html`, boilerplate tags stripped, whitespace collapsed.

    Deterministic and side-effect-free: same HTML in, same text out, every time (needed for
    criterion 14's determinism to hold transitively through to the requirement extraction and
    match report built from this text).
    """
    parser = _MainTextParser()
    parser.feed(html)
    parser.close()

    return collapse_whitespace(parser.text)
