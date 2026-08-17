"""Rank candidate evidence bullets by relevance and recency, and select within a length
budget (criterion 16).

Both functions are pure and fully deterministic: ties are always broken the same way
(history id, then bullet position), so the same profile always ranks/selects the same way.
"""

from __future__ import annotations

from datetime import date

from cv_writer.ingestion.models import RequirementKind
from cv_writer.ingestion.requirements import word_boundary_pattern
from cv_writer.profile.models import Bullet, JobHistory, Profile

from .models import EvidenceBullet, MatchStatus, RequirementMatch

# Rough one-page budget in characters of bullet `result` text — a first cut, not the final
# page-fit algorithm (that's criterion 24/26, slice 4, measured against the real PDF template).
DEFAULT_LENGTH_BUDGET_CHARS = 2_200


def _histories_by_id(profile: Profile) -> dict[str, JobHistory]:
    return {history.id: history for history in profile.job_histories}


def rank_evidence_bullets(
    profile: Profile, skill_value: str, history_ids: list[str]
) -> list[EvidenceBullet]:
    """Rank bullets across `history_ids` (the histories evidencing this skill) by relevance —
    does the bullet's own STAR text mention the skill? — then recency — newer job histories
    first, "present" counting as newest. Ties break on (history_id, bullet_index) so the order
    never depends on dict/set iteration order.
    """
    histories_by_id = _histories_by_id(profile)

    scored: list[tuple[int, int, str, int]] = []
    for history_id in history_ids:
        history = histories_by_id.get(history_id)
        if history is None:
            continue  # dangling evidence id; Profile's own validator should prevent this
        recency = _recency_ordinal(history)
        for index, bullet in enumerate(history.bullets):
            relevance = _relevance_score(bullet, skill_value)
            scored.append((relevance, recency, history_id, index))

    scored.sort(key=lambda item: (-item[0], -item[1], item[2], item[3]))
    return [
        EvidenceBullet(history_id=h, bullet_index=i, rank_score=float(relevance))
        for relevance, _recency, h, i in scored
    ]


def select_bullets_within_budget(
    matches: list[RequirementMatch],
    profile: Profile,
    *,
    max_chars: int = DEFAULT_LENGTH_BUDGET_CHARS,
) -> list[EvidenceBullet]:
    """Greedily select bullets to feature across all matched/partial requirements' ranked
    evidence, most important requirement first. A bullet that would push the running total
    over `max_chars` of bullet `result` text is skipped, not treated as a stopping point — a
    smaller, lower-priority bullet appearing later is still considered, so the budget gets used
    as fully as possible rather than leaving it unspent because one oversized bullet came first.
    A bullet evidencing more than one requirement is selected once. Always keeps at least one
    bullet even if it alone exceeds the budget, so a single very long bullet can't zero out the
    selection entirely.
    """
    histories_by_id = _histories_by_id(profile)

    ordered = sorted(
        (m for m in matches if m.status != MatchStatus.MISSING and m.evidence_bullets),
        key=lambda m: (_requirement_priority(m), m.requirement.value),
    )

    selected: list[EvidenceBullet] = []
    seen: set[tuple[str, int]] = set()
    total_chars = 0
    for match in ordered:
        for evidence in match.evidence_bullets:
            key = (evidence.history_id, evidence.bullet_index)
            if key in seen:
                continue
            history = histories_by_id.get(evidence.history_id)
            if history is None or evidence.bullet_index >= len(history.bullets):
                continue
            bullet_len = len(history.bullets[evidence.bullet_index].result)
            if selected and total_chars + bullet_len > max_chars:
                continue
            selected.append(evidence)
            seen.add(key)
            total_chars += bullet_len

    return selected


def _requirement_priority(match: RequirementMatch) -> int:
    order = {
        RequirementKind.REQUIRED_SKILL: 0,
        RequirementKind.SENIORITY: 1,
        RequirementKind.LANGUAGE: 1,
        RequirementKind.PREFERRED_SKILL: 2,
        RequirementKind.LOCATION_WORK_MODEL: 3,
    }
    return order.get(match.requirement.kind, 9)


def _recency_ordinal(history: JobHistory) -> int:
    end = date.max if history.end_date == "present" else history.end_date
    return end.toordinal()


def _relevance_score(bullet: Bullet, skill_value: str) -> int:
    # Word-boundary matches, not a plain substring count: skill_value="react" must not count a
    # bullet that only mentions "reactive" (same false-positive class requirements.py's phrase
    # matching and matcher.py's fuzzy skill matching both guard against — see
    # word_boundary_pattern's docstring).
    haystack = " ".join([bullet.situation, bullet.task, bullet.action, bullet.result])
    return len(word_boundary_pattern(skill_value).findall(haystack))
