"""Criteria 17-19a: every generated bullet carries the id of the profile bullet (or the
per-application extra input) it was derived from. `source_ids` is the one place that resolves
a bare string id to either, and the one place that turns a matching-layer `EvidenceBullet`
(history_id + bullet_index — a ranking candidate) into a citable id. See ADR 0004 decision 1.
"""

from datetime import date

import pytest

from cv_writer.generation.models import ExtraInput, ExtraInputKind
from cv_writer.generation.source_ids import (
    all_valid_source_ids,
    bullet_source_id,
    resolve_source,
)
from cv_writer.matching.models import EvidenceBullet
from cv_writer.profile.models import Bullet, Identity, JobHistory, Metric, Profile


@pytest.fixture
def profile() -> Profile:
    history = JobHistory(
        id="job-acme",
        company="Acme Corp",
        role_title="Backend Engineer",
        country="Portugal",
        area="Engineering",
        start_date=date(2020, 1, 15),
        end_date="present",
        bullets=[
            Bullet(
                id="job-acme-b1",
                situation="S1",
                task="T1",
                action="A1",
                result="R1",
                metric=Metric(value="+10%"),
            ),
            Bullet(id="job-acme-b2", situation="S2", task="T2", action="A2", result="R2"),
            Bullet(id="job-acme-b3", situation="S3", task="T3", action="A3", result="R3"),
        ],
    )
    return Profile(
        identity=Identity(name="Ana Example", email="ana@example.com"),
        job_histories=[history],
        skills=[],
    )


@pytest.fixture
def extra_inputs() -> list[ExtraInput]:
    return [ExtraInput(id="extra-1", kind=ExtraInputKind.EMPHASIS, text="Emphasize backend work")]


def test_bullet_source_id_resolves_an_evidence_bullet_to_its_profile_bullet_id(profile):
    evidence = EvidenceBullet(history_id="job-acme", bullet_index=1, rank_score=0)

    assert bullet_source_id(profile, evidence) == "job-acme-b2"


def test_resolve_source_finds_a_profile_bullet_by_id(profile, extra_inputs):
    result = resolve_source("job-acme-b1", profile, extra_inputs)

    assert isinstance(result, Bullet)
    assert result.id == "job-acme-b1"


def test_resolve_source_finds_an_extra_input_by_id(profile, extra_inputs):
    result = resolve_source("extra-1", profile, extra_inputs)

    assert isinstance(result, ExtraInput)
    assert result.id == "extra-1"


def test_resolve_source_returns_none_for_an_unknown_id(profile, extra_inputs):
    assert resolve_source("does-not-exist", profile, extra_inputs) is None


def test_all_valid_source_ids_includes_both_profile_bullets_and_extra_input(profile, extra_inputs):
    ids = all_valid_source_ids(profile, extra_inputs)

    assert ids == {"job-acme-b1", "job-acme-b2", "job-acme-b3", "extra-1"}


def test_resolve_source_raises_on_a_collision_between_a_bullet_and_an_extra_input_id(profile):
    # Regression: a silent "bullets checked first" preference would let a fabricated numeric
    # claim from unverifiable extra-input text resolve against an unrelated real bullet's
    # Metric, bypassing the "extra input has no metric" rule (ADR 0004 decision 7).
    colliding_extra = [
        ExtraInput(id="job-acme-b1", kind=ExtraInputKind.EMPHASIS, text="Collides on purpose")
    ]

    with pytest.raises(ValueError, match="collides"):
        resolve_source("job-acme-b1", profile, colliding_extra)


def test_bullet_source_id_raises_on_a_stale_bullet_index(profile):
    stale = EvidenceBullet(history_id="job-acme", bullet_index=99, rank_score=0)

    with pytest.raises(ValueError, match="does not resolve"):
        bullet_source_id(profile, stale)


def test_bullet_source_id_raises_on_an_unknown_history_id(profile):
    stale = EvidenceBullet(history_id="does-not-exist", bullet_index=0, rank_score=0)

    with pytest.raises(ValueError, match="does not resolve"):
        bullet_source_id(profile, stale)
