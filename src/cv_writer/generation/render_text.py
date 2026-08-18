"""Criteria 25, 27: each generated CV is written as Markdown — the versionable, diffable
source — and a plain-text variant is produced for job boards that reject PDFs, carrying the
same content with no layout-dependent formatting.

Deliberately simple, single-section layout for this slice: one "Experience" section listing
the accepted, validated bullets, plus Education/Skills pulled straight from the profile. This
is the content render_html.py wraps in the visual print template.
"""

from __future__ import annotations

from cv_writer.profile.models import Profile

from .models import GeneratedCv


def render_markdown(cv: GeneratedCv, profile: Profile) -> str:
    """The full CV as Markdown (criterion 25) — the source both the plain-text variant and
    the PDF template are built from."""
    lines = [f"# {profile.identity.name}"]
    lines.append(_contact_line(profile))
    if profile.identity.links:
        lines.append(" | ".join(f"{name}: {url}" for name, url in profile.identity.links.items()))

    lines.append("")
    lines.append("## Experience")
    lines.extend(f"- {bullet.text}" for bullet in cv.accepted_bullets)

    if profile.education:
        lines.append("")
        lines.append("## Education")
        lines.extend(f"- {edu.degree}, {edu.institution}" for edu in profile.education)

    if profile.skills:
        lines.append("")
        lines.append("## Skills")
        lines.append(", ".join(skill.name for skill in profile.skills))

    return "\n".join(lines)


def render_plain_text(cv: GeneratedCv, profile: Profile) -> str:
    """The same content as render_markdown(), with Markdown syntax stripped (criterion 27) —
    heading marks and bullet markers, since job boards that reject PDFs generally want plain
    prose, not Markdown source."""
    lines = []
    for line in render_markdown(cv, profile).splitlines():
        stripped = line.lstrip("#").strip()
        if stripped.startswith("- "):
            stripped = stripped[2:]
        lines.append(stripped)
    return "\n".join(lines)


def _contact_line(profile: Profile) -> str:
    bits = [profile.identity.email]
    if profile.identity.phone:
        bits.append(profile.identity.phone)
    if profile.identity.location:
        bits.append(profile.identity.location)
    return " | ".join(bits)
