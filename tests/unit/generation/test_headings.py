"""AC-004: render_markdown()'s three structural strings -- the experience, education and
skills section headings -- must exist in every supported language, not just English. This
module (headings.py) is the localized mapping render_text.py looks them up from.

Contract C-006 pins today's English output byte-for-byte (nothing else in the suite asserts
on render_markdown()'s actual output -- the `## Experience` strings elsewhere under tests/ are
hand-written Markdown *inputs* to render_html/page_fit, never assertions on what
render_markdown() itself emits), so this is the only thing stopping the English CV from
silently drifting while the other three languages are added.
"""

from __future__ import annotations

import pytest

from cv_writer.generation.headings import SECTION_HEADINGS, section_headings
from cv_writer.generation.language import SUPPORTED_LANGUAGES


def test_english_headings_are_pinned_byte_for_byte():
    # Today's rendered output, pinned exactly -- nothing else in the suite asserts this, so
    # this is what stops the English CV silently drifting while the other three languages
    # are added.
    headings = section_headings("english")

    assert headings.experience == "Experience"
    assert headings.education == "Education"
    assert headings.skills == "Skills"


@pytest.mark.parametrize("language", ["portuguese", "german", "spanish"])
def test_non_english_headings_are_non_empty_and_differ_from_english(language):
    english = section_headings("english")
    headings = section_headings(language)

    assert headings.experience.strip() != ""
    assert headings.education.strip() != ""
    assert headings.skills.strip() != ""
    assert headings.experience != english.experience
    assert headings.education != english.education
    assert headings.skills != english.skills


def test_section_headings_normalizes_case_and_surrounding_whitespace():
    # GeneratedCv.language is a free str field (no Enum), so a capitalized or padded value
    # must not raise.
    assert section_headings("English") == section_headings("english")
    assert section_headings("  english  ") == section_headings("english")


def test_section_headings_covers_exactly_the_supported_languages():
    assert set(SECTION_HEADINGS) == set(SUPPORTED_LANGUAGES)


def test_section_headings_raises_on_an_unsupported_language():
    # Design decision 4: no silent English fallback (L-004) -- a language this tool has no
    # heading translation for must fail loudly, not render the wrong document.
    with pytest.raises(ValueError) as excinfo:
        section_headings("french")

    message = str(excinfo.value)
    assert "french" in message
    for language in SUPPORTED_LANGUAGES:
        assert language in message
