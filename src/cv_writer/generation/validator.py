"""Criterion 19 — the anti-fabrication guarantee: a validator rejects a generated CV that
contains (a) a bullet with no source id, (b) an employer/title/date/credential absent from
the profile, or (c) a numeric claim not present in its source bullet's metrics. Rejection
always names the offending line. See ADR 0004 decision 7 for the numeric-claim algorithm's
worked examples and its documented "metrics only, not full STAR text" trade-off.

The LLM's own citation (GeneratedBulletDraft.source_id) is never trusted on its say-so —
every check here independently re-derives the truth from the profile itself.
"""

from __future__ import annotations

import re

from cv_writer.profile.models import Bullet, Metric, Profile

from .models import ExtraInput, RephraseOutput, ValidationFailure
from .source_ids import resolve_source

# Deliberately permissive: over-extracting candidate tokens is safe (more gets checked
# against the source metric); under-extraction is the real danger, since it would let a
# fabricated number slip through unchecked. Longer suffixes are tried before shorter ones
# that are their own prefix (e.g. "min" before "m") so "10min" doesn't get truncated to "10m".
#
# The leading/trailing (?<![A-Za-z0-9])/(?![A-Za-z0-9]) guards are load-bearing, not
# cosmetic: without them this pattern pulled "99" out of "p99", "8" out of "K8s", "17" out of
# "iOS17" — ordinary technical terms, not numeric claims — and rejected truthful bullets that
# used them near a source bullet with no matching digits (a code-review pass on this slice
# caught it via `extract_numeric_tokens("Cut p99 latency...")`).
_NUMERIC_SUFFIX = (
    r"(?:ms|min|hrs|hr|days|day|weeks|week|months|month|years|year|k|K|m|M|b|B|s|x|%)"
)
_NUMERIC_TOKEN_PATTERN = re.compile(
    rf"(?<![A-Za-z0-9])[+-]?\d+(?:[.,]\d+)?\s?{_NUMERIC_SUFFIX}?(?![A-Za-z0-9])", re.IGNORECASE
)

# A curated (not NLP) signal for whether the bullet's prose claims growth or reduction, so an
# unsigned or wrongly-signed number can still be caught when the words around it contradict
# the source metric's own sign — e.g. "Increased latency by 77%" against a source Metric of
# "-77%" (a decrease). English + Portuguese, matching this checker's own bilingual scope.
_INCREASE_WORDS = {
    "increased", "increase", "grew", "grow", "improved", "improve", "boosted", "boost",
    "raised", "raise", "gained", "gain", "up",
    "aumentou", "aumentar", "aumento", "cresceu", "crescer", "melhorou", "melhorar",
}
_DECREASE_WORDS = {
    "decreased", "decrease", "reduced", "reduce", "cut", "lowered", "lower", "dropped",
    "drop", "shrank", "shrunk", "down",
    "reduziu", "reduzir", "diminuiu", "diminuir", "cortou", "cortar", "baixou",
}

# Deliberately narrow to "at" only: a code-review pass confirmed "for"/"with"/"na"/"no"/"em"
# false-positive constantly on ordinary CV prose ("worked with Python and SQL daily",
# "partnered with Marketing") — those cues precede tools/teams/projects far more often than
# employers, so this heuristic would reject truthful bullets more often than it catches
# fabricated ones. "at <Company>" is the one idiom common and specific enough in English CV
# writing to keep. A lightweight, deterministic heuristic (ADR 0004's "curated pattern
# matching, not NLP" posture) — not full named-entity recognition, and English-only for now.
# Flagged as a "watch this against real postings" heuristic, same posture as the ingestion
# package's curated dictionaries; same ceiling as the PT-PT checker's own open question.
_ENTITY_CUE_PATTERN = re.compile(r"\bat\s+([A-Z][\w&.,'-]*(?:\s+[A-Z][\w&.,'-]*){0,3})")


def extract_numeric_tokens(text: str) -> list[str]:
    """Every candidate numeric claim in `text` — signed numbers with an optional unit/
    duration suffix. See the module docstring for why this is deliberately permissive."""
    return [match.group(0).strip() for match in _NUMERIC_TOKEN_PATTERN.finditer(text)]


def validate_generated_cv(
    draft: RephraseOutput, profile: Profile, extra_inputs: list[ExtraInput]
) -> list[ValidationFailure]:
    """Check every generated bullet against the profile. Returns one ValidationFailure per
    offending bullet (a bullet can fail for only its first-found reason — once a bullet is
    already rejected as having no source id or an unknown one, there's no source to check its
    entities/numbers against anyway)."""
    failures: list[ValidationFailure] = []

    for line_number, bullet_draft in enumerate(draft.bullets, start=1):
        if not bullet_draft.source_id:
            failures.append(
                ValidationFailure(
                    reason="bullet has no source id (criterion 19a)",
                    offending_line=bullet_draft.text,
                    line_number=line_number,
                )
            )
            continue

        source = resolve_source(bullet_draft.source_id, profile, extra_inputs)
        if source is None:
            failures.append(
                ValidationFailure(
                    reason=(
                        f"bullet cites unknown source id {bullet_draft.source_id!r} "
                        "(criterion 19a)"
                    ),
                    offending_line=bullet_draft.text,
                    line_number=line_number,
                )
            )
            continue

        entity_failure = _check_entities(bullet_draft.text, profile)
        if entity_failure is not None:
            failures.append(
                ValidationFailure(
                    reason=(
                        f"bullet names {entity_failure!r}, absent from the profile "
                        "(criterion 19b)"
                    ),
                    offending_line=bullet_draft.text,
                    line_number=line_number,
                )
            )
            continue

        numeric_failure = _check_numeric_claims(bullet_draft.text, source)
        if numeric_failure is not None:
            failures.append(
                ValidationFailure(
                    reason=(
                        f"numeric claim {numeric_failure!r} not present in its source "
                        "bullet's metrics (criterion 19c)"
                    ),
                    offending_line=bullet_draft.text,
                    line_number=line_number,
                )
            )
            continue

        if isinstance(source, Bullet) and source.metric is not None:
            if _direction_mismatch(bullet_draft.text, source.metric):
                failures.append(
                    ValidationFailure(
                        reason=(
                            f"claimed direction contradicts source metric "
                            f"{source.metric.value!r} (criterion 19c)"
                        ),
                        offending_line=bullet_draft.text,
                        line_number=line_number,
                    )
                )
                continue

    return failures


_CORPORATE_SUFFIX_PATTERN = re.compile(
    r",?\s*(inc|ltd|llc|s\.?a\.?|gmbh|corp|co)\.?\s*$", re.IGNORECASE
)


def _check_entities(bullet_text: str, profile: Profile) -> str | None:
    """Return the first cue-phrase entity mention that isn't anywhere in the profile's known
    companies/role titles/education institutions/degrees, or None if every mention checks
    out. Comparison is normalized (lowercased, common corporate suffixes like ", Inc."
    stripped) and allows either name to be a substring of the other — a code-review pass
    found the original exact-match comparison rejected a truthful "at Stripe" against a
    profile company of "Stripe, Inc." Trade-off, deliberately accepted: this is more
    permissive than exact matching, so a fabricated name that happens to share a substring
    with a real one could in principle slip through — favoring fewer false rejections of
    truthful content over maximum strictness, same posture as this checker's other
    heuristics."""
    known_entities = _known_entities(profile)
    for match in _ENTITY_CUE_PATTERN.finditer(bullet_text):
        candidate_raw = match.group(1).rstrip(".,;:")
        candidate = _normalize_entity_name(candidate_raw)
        if not any(candidate == known or candidate in known or known in candidate
                    for known in known_entities):
            return candidate_raw
    return None


def _normalize_entity_name(name: str) -> str:
    return _CORPORATE_SUFFIX_PATTERN.sub("", name).strip().rstrip(",.").lower()


def _known_entities(profile: Profile) -> set[str]:
    entities: set[str] = set()
    for history in profile.job_histories:
        entities.add(_normalize_entity_name(history.company))
        entities.add(_normalize_entity_name(history.role_title))
    for education in profile.education:
        entities.add(_normalize_entity_name(education.institution))
        entities.add(_normalize_entity_name(education.degree))
    return entities


def _check_numeric_claims(bullet_text: str, source: Bullet | ExtraInput) -> str | None:
    """Return the first numeric token not backed by the source's metrics, or None if every
    extracted token checks out. A source with no Metric (or an ExtraInput, which never has
    one) rejects any numeric claim at all — see ADR 0004 decision 7."""
    tokens = extract_numeric_tokens(bullet_text)
    if not tokens:
        return None

    metric = source.metric if isinstance(source, Bullet) else None
    if metric is None:
        return tokens[0]

    haystack = f"{metric.value} {metric.unit or ''} {metric.baseline or ''}".lower()
    for token in tokens:
        if not _token_matches_haystack(token.lower(), haystack):
            return token
    return None


def _direction_mismatch(bullet_text: str, metric: Metric) -> bool:
    """True if the bullet's prose claims the opposite direction from the source metric's own
    sign — e.g. "Increased latency by 77%" against a true Metric of "-77%" (a decrease).
    Numeral matching alone (`_check_numeric_claims`) can't catch this: "77%" is a substring
    of "-77%" either way. A curated word list, not NLP (this checker's established posture);
    silent when the metric has no explicit sign or the bullet uses neither word set."""
    if not metric.value or metric.value[0] not in "+-":
        return False
    metric_sign = metric.value[0]

    words = set(re.findall(r"[^\W\d_]+", bullet_text.lower(), re.UNICODE))
    claims_increase = bool(words & _INCREASE_WORDS)
    claims_decrease = bool(words & _DECREASE_WORDS)

    if metric_sign == "-" and claims_increase and not claims_decrease:
        return True
    if metric_sign == "+" and claims_decrease and not claims_increase:
        return True
    return False


def _token_matches_haystack(token: str, haystack: str) -> bool:
    """Plain substring containment was too permissive: a fabricated "7%" is a substring of
    the true "-77%", and a fabricated "20ms" is a substring of the true "320ms" — both are
    real numbers that were never actually claimed. A match only counts if it isn't itself
    embedded inside a larger digit run in the haystack (not immediately preceded or followed
    by another digit), so the token must appear as a standalone number, not a fragment of one.
    """
    for match in re.finditer(re.escape(token), haystack):
        start, end = match.span()
        before = haystack[start - 1] if start > 0 else ""
        after = haystack[end] if end < len(haystack) else ""
        if before.isdigit() or after.isdigit():
            continue
        return True
    return False
