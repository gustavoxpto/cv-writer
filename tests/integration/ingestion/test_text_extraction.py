"""Criterion 7: the tool extracts the main text of a fetched posting page."""

from cv_writer.ingestion.text_extraction import extract_main_text


def test_extract_main_text_strips_script_style_nav_header_footer():
    html = """
    <html>
      <head><style>body { color: red; }</style></head>
      <body>
        <nav>Home | About | Careers</nav>
        <header>Acme Corp</header>
        <script>console.log('tracking pixel');</script>
        <main>
          <h1>Senior Backend Engineer</h1>
          <p>We need someone who loves Python and SQL.</p>
        </main>
        <footer>&copy; 2026 Acme Corp. All rights reserved.</footer>
      </body>
    </html>
    """

    text = extract_main_text(html)

    assert "Senior Backend Engineer" in text
    assert "loves Python and SQL" in text
    assert "Home | About | Careers" not in text
    assert "Acme Corp" not in text
    assert "tracking pixel" not in text
    assert "All rights reserved" not in text


def test_extract_main_text_separates_block_elements_with_line_breaks():
    html = "<ul><li>Python</li><li>SQL</li><li>Docker</li></ul>"

    text = extract_main_text(html)

    lines = text.splitlines()
    assert lines == ["Python", "SQL", "Docker"]


def test_extract_main_text_is_deterministic():
    html = "<body><p>Same input,</p><p>same output.</p></body>"

    assert extract_main_text(html) == extract_main_text(html)


def test_extract_main_text_separates_adjacent_inline_elements_with_no_source_whitespace():
    # Regression: a naive "".join of data chunks merges adjacent inline elements with nothing
    # between them in the source into one unmatchable token ("PythonSQL") — a common pattern
    # for skill-pill/badge markup on real job boards.
    html = "<div><span>Python</span><span>SQL</span></div>"

    text = extract_main_text(html)

    assert "PythonSQL" not in text
    assert "Python" in text
    assert "SQL" in text


def test_extract_main_text_collapses_runs_of_whitespace():
    html = "<p>Python   and     SQL</p>"

    assert extract_main_text(html) == "Python and SQL"


def test_extract_main_text_documents_the_unclosed_boilerplate_tag_limitation():
    # Known limitation (see module docstring): html.parser has no HTML5-style error recovery,
    # so a boilerplate tag that's never properly closed anywhere in malformed markup suppresses
    # everything after it. This test documents that behaviour rather than hiding it — the
    # safety net is fetch_tier1's min-chars escalation to tier 2's real browser, proven in
    # test_pipeline.py's test_ingest_from_url_recovers_via_tier2_from_malformed_tier1_markup.
    html = "<nav>menu</div><h1>Senior Backend Engineer</h1><p>Requirements: Python, SQL</p>"

    assert extract_main_text(html) == ""
