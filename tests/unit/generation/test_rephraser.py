"""Criteria 18, 22, 23: the LLM's role is bounded to rephrasing/ordering selected evidence,
every generated bullet cites its source id; the LLM call sits behind one interface tests
replace with a fake responder, so the whole pipeline is testable offline with no API key and
no network; the real key is only ever read from the environment at call time (never here —
these tests only ever touch FakeRephraser).
"""

from datetime import date

import pytest

from cv_writer.generation.models import ExtraInput, ExtraInputKind
from cv_writer.generation.rephraser import FakeRephraser, RephraseRequest
from cv_writer.profile.models import Bullet, JobHistory, Metric


@pytest.fixture
def history() -> JobHistory:
    return JobHistory(
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
                result="Cut p99 latency from 1.4s to 320ms.",
                metric=Metric(value="-77%"),
            ),
            Bullet(id="job-acme-b2", situation="S2", task="T2", action="A2", result="R2"),
            Bullet(id="job-acme-b3", situation="S3", task="T3", action="A3", result="R3"),
        ],
    )


def test_fake_rephraser_default_behavior_echoes_evidence_bullets_with_their_real_source_ids(
    history,
):
    request = RephraseRequest(
        evidence_bullets=[history.bullets[0]],
        extra_inputs=[],
        target_language="english",
        target_variant=None,
        posting_text="Senior backend engineer wanted.",
    )
    rephraser = FakeRephraser()

    output = rephraser.rephrase(request)

    assert len(output.bullets) == 1
    assert output.bullets[0].source_id == "job-acme-b1"
    assert output.bullets[0].text == "Cut p99 latency from 1.4s to 320ms."


def test_fake_rephraser_default_behavior_includes_extra_input(history):
    extra = ExtraInput(id="extra-1", kind=ExtraInputKind.ACHIEVEMENT, text="Led a migration.")
    request = RephraseRequest(
        evidence_bullets=[history.bullets[0]],
        extra_inputs=[extra],
        target_language="english",
        target_variant=None,
        posting_text="Senior backend engineer wanted.",
    )
    rephraser = FakeRephraser()

    output = rephraser.rephrase(request)

    source_ids = {b.source_id for b in output.bullets}
    assert "extra-1" in source_ids


def test_fake_rephraser_with_a_fixed_response_returns_it_verbatim_no_network(history):
    from cv_writer.generation.models import GeneratedBulletDraft, RephraseOutput

    canned = RephraseOutput(
        bullets=[
            GeneratedBulletDraft(
                text="Fabricated claim of 999% growth.", source_id="job-acme-b1"
            )
        ]
    )
    rephraser = FakeRephraser(fixed_response=canned)
    request = RephraseRequest(
        evidence_bullets=[history.bullets[0]],
        extra_inputs=[],
        target_language="english",
        target_variant=None,
        posting_text="...",
    )

    output = rephraser.rephrase(request)

    assert output == canned
