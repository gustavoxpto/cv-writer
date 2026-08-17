"""Criterion 16: rank candidate evidence bullets by relevance and recency, then select bullets
to feature within a length budget."""

from cv_writer.ingestion.models import Requirement, RequirementKind
from cv_writer.matching.models import EvidenceBullet, MatchStatus, RequirementMatch
from cv_writer.matching.ranking import rank_evidence_bullets, select_bullets_within_budget


def test_rank_evidence_bullets_prefers_more_recent_histories(profile):
    ranked = rank_evidence_bullets(profile, "python", ["job-acme", "job-globex"])

    # every job-globex bullet (2022-07-01 -> present) outranks every job-acme bullet
    # (2020-01-15 -> 2022-06-30), since none of the fixture bullets mention "python" by name
    # and recency is the only remaining signal.
    history_order = [bullet.history_id for bullet in ranked]
    last_globex_index = max(i for i, h in enumerate(history_order) if h == "job-globex")
    first_acme_index = min(i for i, h in enumerate(history_order) if h == "job-acme")
    assert last_globex_index < first_acme_index


def test_rank_evidence_bullets_prefers_relevance_over_recency():
    from datetime import date

    from cv_writer.profile.models import Bullet, Identity, JobHistory, Metric, Profile

    def bullet(text, metric=None):
        return Bullet(situation=text, task=text, action=text, result=text, metric=metric)

    older = JobHistory(
        id="older",
        company="A",
        role_title="Engineer",
        country="Portugal",
        area="Eng",
        start_date=date(2015, 1, 1),
        end_date=date(2017, 1, 1),
        bullets=[
            bullet("Wrote a Python service", metric=Metric(value="+1", unit="x")),
            bullet("Filed some paperwork"),
            bullet("Attended meetings"),
        ],
    )
    newer = JobHistory(
        id="newer",
        company="B",
        role_title="Engineer",
        country="Portugal",
        area="Eng",
        start_date=date(2023, 1, 1),
        end_date="present",
        bullets=[
            bullet("Managed the office snack budget", metric=Metric(value="+1", unit="x")),
            bullet("Organized team lunches"),
            bullet("Booked meeting rooms"),
        ],
    )
    profile = Profile(
        identity=Identity(name="X", email="x@example.com"),
        job_histories=[older, newer],
        skills=[],
    )

    ranked = rank_evidence_bullets(profile, "python", ["older", "newer"])

    assert ranked[0].history_id == "older"
    assert ranked[0].bullet_index == 0


def test_rank_evidence_bullets_uses_word_boundaries_not_plain_substrings():
    # Regression: plain substring counting made a bullet mentioning "reactive" score as
    # relevant to skill_value="react", even though it never mentions React.
    from datetime import date

    from cv_writer.profile.models import Bullet, Identity, JobHistory, Metric, Profile

    def bullet(text, metric=None):
        return Bullet(situation=text, task=text, action=text, result=text, metric=metric)

    history = JobHistory(
        id="job",
        company="A",
        role_title="Engineer",
        country="Portugal",
        area="Eng",
        start_date=date(2020, 1, 1),
        end_date="present",
        bullets=[
            bullet("Built a reactive UI using Vue", metric=Metric(value="+1", unit="x")),
            bullet("Wrote documentation"),
            bullet("Reviewed pull requests"),
        ],
    )
    profile = Profile(
        identity=Identity(name="X", email="x@example.com"),
        job_histories=[history],
        skills=[],
    )

    ranked = rank_evidence_bullets(profile, "react", ["job"])

    assert all(b.rank_score == 0 for b in ranked)


def test_rank_evidence_bullets_is_deterministic(profile):
    first = rank_evidence_bullets(profile, "python", ["job-acme", "job-globex"])
    second = rank_evidence_bullets(profile, "python", ["job-acme", "job-globex"])

    assert [b.model_dump() for b in first] == [b.model_dump() for b in second]


def _match(
    value, evidence_bullets, kind=RequirementKind.REQUIRED_SKILL, status=MatchStatus.MATCHED
):
    return RequirementMatch(
        requirement=Requirement(kind=kind, value=value, source_phrase=value),
        status=status,
        evidence_bullets=evidence_bullets,
    )


def test_select_bullets_within_budget_stops_before_exceeding_the_budget(profile):
    matches = [
        _match(
            "python",
            [
                EvidenceBullet(history_id="job-globex", bullet_index=0, rank_score=0),
                EvidenceBullet(history_id="job-globex", bullet_index=1, rank_score=0),
                EvidenceBullet(history_id="job-acme", bullet_index=0, rank_score=0),
            ],
        )
    ]

    bullet_len = len(profile.job_histories[1].bullets[0].result)
    selected = select_bullets_within_budget(matches, profile, max_chars=bullet_len)

    assert len(selected) == 1
    assert selected[0].history_id == "job-globex"
    assert selected[0].bullet_index == 0


def test_select_bullets_within_budget_always_keeps_at_least_one_bullet(profile):
    matches = [
        _match("python", [EvidenceBullet(history_id="job-globex", bullet_index=0, rank_score=0)])
    ]

    selected = select_bullets_within_budget(matches, profile, max_chars=1)

    assert len(selected) == 1


def test_select_bullets_within_budget_never_selects_the_same_bullet_twice(profile):
    shared = EvidenceBullet(history_id="job-globex", bullet_index=0, rank_score=0)
    matches = [
        _match("python", [shared]),
        _match("fastapi", [shared], kind=RequirementKind.PREFERRED_SKILL),
    ]

    selected = select_bullets_within_budget(matches, profile, max_chars=10_000)

    assert len(selected) == 1


def test_select_bullets_within_budget_skips_missing_requirements(profile):
    matches = [
        _match(
            "rust",
            [EvidenceBullet(history_id="job-globex", bullet_index=0, rank_score=0)],
            status=MatchStatus.MISSING,
        )
    ]

    selected = select_bullets_within_budget(matches, profile, max_chars=10_000)

    assert selected == []
