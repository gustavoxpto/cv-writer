"""Shared in-memory profile builders for matching tests — no file I/O, since the matching
functions under test are pure (criteria 13-16)."""

from __future__ import annotations

from datetime import date

import pytest

from cv_writer.profile.models import Bullet, Identity, JobHistory, Language, Metric, Profile, Skill


def _bullet(text: str, *, metric: Metric | None = None) -> Bullet:
    return Bullet(
        situation=f"{text} — situation",
        task=f"{text} — task",
        action=f"{text} — action, using Python and SQL daily",
        result=f"{text} — result",
        metric=metric,
    )


@pytest.fixture
def profile() -> Profile:
    """A profile with an evidenced skill (Python), an unevidenced one (Docker), a language
    at working proficiency (English) and one below it (German), and two job histories spanning
    2020-01-15 to "present" (~6.6 years as of 2026-08-17, the tests' reference date)."""
    acme = JobHistory(
        id="job-acme",
        company="Acme Corp",
        role_title="Backend Engineer",
        country="Portugal",
        area="Engineering",
        start_date=date(2020, 1, 15),
        end_date=date(2022, 6, 30),
        bullets=[
            _bullet("Cut checkout latency"),
            _bullet("Automated deploys", metric=Metric(value="-95%", unit="deploy time")),
            _bullet("Wrote onboarding guide"),
        ],
    )
    globex = JobHistory(
        id="job-globex",
        company="Globex",
        role_title="Senior Backend Engineer",
        country="Portugal",
        area="Engineering",
        start_date=date(2022, 7, 1),
        end_date="present",
        bullets=[
            _bullet("Built profile schema", metric=Metric(value="100%", unit="coverage")),
            _bullet("Reduced search latency"),
            _bullet("Standardized incident reviews"),
        ],
    )
    return Profile(
        identity=Identity(name="Ana Example", email="ana@example.com"),
        languages=[
            Language(name="English", proficiency="professional"),
            Language(name="German", proficiency="basic"),
        ],
        job_histories=[acme, globex],
        skills=[
            Skill(name="Python", category="language", evidence=["job-acme", "job-globex"]),
            Skill(name="Docker", category="tool", evidence=[]),
        ],
    )


@pytest.fixture
def reference_date() -> date:
    return date(2026, 8, 17)
