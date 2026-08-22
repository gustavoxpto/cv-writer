"""AC-004: render_markdown() emits the experience, education and skills section headings in
the CV's resolved language (cv.language), not hardcoded English. render_plain_text() derives
from render_markdown() and inherits this by construction.

render_markdown() has no unit test today (it is only exercised indirectly through
write_output.py/render_html.py fixtures), so this file is new. The shared fixture below is
pinned here rather than imported, and its *profile-authored* content deliberately contains
none of the words "Experience", "Education", "Skills" -- so the negative, non-English
assertions below can only be about headings, never about an English bullet, skill name, or
degree title that happens to share a word with a heading (contract C-006).
"""

from __future__ import annotations

import pytest

from cv_writer.generation.headings import section_headings
from cv_writer.generation.language import SUPPORTED_LANGUAGES
from cv_writer.generation.models import GeneratedBulletDraft, GeneratedCv
from cv_writer.generation.render_text import render_markdown, render_plain_text
from cv_writer.profile.models import Education, Identity, Profile, Skill


def _profile() -> Profile:
    return Profile(
        identity=Identity(name="Ana Example", email="ana@example.com"),
        education=[
            Education(institution="Universidade de Lisboa", degree="Licenciatura em Informática"),
        ],
        skills=[Skill(name="Python", category="engineering")],
    )


def _cv(language: str) -> GeneratedCv:
    return GeneratedCv(
        markdown="- Cut deployment time by 60%.",
        language=language,
        variant=None,
        source_ids_used=["job-acme-b1"],
        accepted_bullets=[
            GeneratedBulletDraft(text="Cut deployment time by 60%.", source_id="job-acme-b1")
        ],
    )


def test_fixture_profile_authored_content_carries_none_of_the_heading_words():
    # Guards the negative assertions below: if this ever fails, they would too, for the
    # wrong reason.
    profile = _profile()
    cv = _cv("english")
    authored_text = " ".join(
        [
            profile.identity.name,
            profile.identity.email,
            *(f"{edu.degree} {edu.institution}" for edu in profile.education),
            *(skill.name for skill in profile.skills),
            *(bullet.text for bullet in cv.accepted_bullets),
        ]
    )
    for word in ("Experience", "Education", "Skills"):
        assert word not in authored_text


@pytest.mark.parametrize("language", sorted(SUPPORTED_LANGUAGES))
def test_render_markdown_uses_the_resolved_language_headings(language):
    headings = section_headings(language)

    rendered = render_markdown(_cv(language), _profile())

    assert f"## {headings.experience}" in rendered
    assert f"## {headings.education}" in rendered
    assert f"## {headings.skills}" in rendered


@pytest.mark.parametrize("language", ["portuguese", "german", "spanish"])
def test_render_markdown_emits_no_english_heading_for_a_non_english_language(language):
    rendered = render_markdown(_cv(language), _profile())

    heading_lines = [line for line in rendered.splitlines() if line.startswith("## ")]

    for heading_line in heading_lines:
        assert "Experience" not in heading_line
        assert "Education" not in heading_line
        assert "Skills" not in heading_line


def test_render_markdown_english_regression_is_unchanged():
    rendered = render_markdown(_cv("english"), _profile())

    assert "## Experience" in rendered
    assert "## Education" in rendered
    assert "## Skills" in rendered


def test_render_plain_text_carries_non_english_headings_with_markdown_markers_stripped():
    headings = section_headings("german")

    rendered = render_plain_text(_cv("german"), _profile())

    assert headings.experience in rendered
    assert headings.education in rendered
    assert headings.skills in rendered
    # The half that actually fails if the "## " markers are not stripped -- the presence
    # checks above alone would pass even on un-stripped Markdown.
    assert f"## {headings.experience}" not in rendered
    assert f"## {headings.education}" not in rendered
    assert f"## {headings.skills}" not in rendered
