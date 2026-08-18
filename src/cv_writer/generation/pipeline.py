"""Criteria 17-23: orchestrate rephrase -> validate -> PT-PT check -> accept/reject. This is
the module integration tests drive with FakeRephraser (criterion 22) — never a real network
call in this repo's test suite.

Rendering to Markdown/HTML/PDF/plain-text (criteria 25-27) and the real page-fit algorithm
(criterion 24) are deliberately out of scope here — see render_text.py/render_html.py/
render_pdf.py/page_fit.py. This module's job ends at "here is an accepted, truthful,
language-correct, PT-PT-clean set of generated bullets," which those modules then render.
"""

from __future__ import annotations

from cv_writer.ingestion.models import Posting
from cv_writer.matching.models import EvidenceBullet, MatchReport

# A first-cut evidence budget, matching matching/ranking.py's own DEFAULT_LENGTH_BUDGET_CHARS
# — page_fit.py (criterion 24) replaces this with the real, PDF-measured algorithm; this
# pipeline only needs *some* bounded set of evidence to hand the Rephraser.
from cv_writer.matching.ranking import select_bullets_within_budget
from cv_writer.profile.models import Bullet, Profile

from .language import resolve_output_language
from .models import ExtraInput, GeneratedCv, GenerationFailure
from .pt_pt_checker import check_pt_pt, load_pt_pt_terms
from .rephraser import Rephraser, RephraseRequest
from .validator import validate_generated_cv


def generate_cv(
    *,
    profile: Profile,
    posting: Posting,
    match_report: MatchReport,
    extra_inputs: list[ExtraInput],
    rephraser: Rephraser,
    language_override: str | None = None,
) -> GeneratedCv | GenerationFailure:
    """Run the full generation + guardrail pipeline for one application. Never raises on a
    "normal" rejection (bad language, fabricated content, brasileirismos) — those are
    GenerationFailure, an ordinary return value, matching ingestion/models.py's
    Posting/IngestionFailure "result vs failure" pattern.
    """
    # Loaded once here and threaded through both call sites that need it below — cheap either
    # way, but there's no reason to read+parse+validate the same file from disk twice for one
    # request (a code-review pass on this slice flagged the earlier, wasteful double load).
    pt_terms = load_pt_pt_terms()

    language_resolution = resolve_output_language(
        posting, profile, override=language_override, pt_terms=pt_terms
    )
    if not language_resolution.allowed:
        return GenerationFailure(reason=language_resolution.reason or "language not allowed")

    evidence = select_bullets_within_budget(match_report.matches, profile)
    evidence_bullets = _resolve_evidence_bullets(profile, evidence)

    request = RephraseRequest(
        evidence_bullets=evidence_bullets,
        extra_inputs=extra_inputs,
        target_language=language_resolution.detected,
        target_variant=language_resolution.variant,
        posting_text=posting.raw_text,
    )
    draft = rephraser.rephrase(request)

    if not draft.bullets:
        # No evidence survived matching/selection (or the Rephraser genuinely produced
        # nothing) — an honest GenerationFailure, not an attempt to build a GeneratedCv with
        # empty content that would fail its own min_length constraint. A code-review pass
        # found the latter: this used to raise an uncaught pydantic ValidationError instead
        # of the ordinary GenerationFailure return value generate_cv()'s own docstring
        # promises for every "normal" rejection.
        return GenerationFailure(reason="no evidence available to generate a CV from")

    validation_failures = validate_generated_cv(draft, profile, extra_inputs)
    if validation_failures:
        return GenerationFailure(
            reason="anti-fabrication validation failed (criterion 19)",
            validation_failures=validation_failures,
        )

    bullets_markdown = "\n".join(f"- {bullet.text}" for bullet in draft.bullets)

    if language_resolution.variant == "pt-pt":
        violations = check_pt_pt(bullets_markdown, terms=pt_terms)
        if violations:
            return GenerationFailure(
                reason="brasileirismos found — blocks acceptance until resolved (criterion 21)",
                pt_pt_violations=violations,
            )

    return GeneratedCv(
        markdown=bullets_markdown,
        language=language_resolution.detected,
        variant=language_resolution.variant,
        source_ids_used=[bullet.source_id for bullet in draft.bullets],
        accepted_bullets=draft.bullets,
    )


def _resolve_evidence_bullets(
    profile: Profile, evidence: list[EvidenceBullet]
) -> list[Bullet]:
    # Deliberately resolves to full Bullet objects here, not just their ids via
    # source_ids.bullet_source_id() — the Rephraser needs each bullet's full STAR text and
    # Metric to work from (RephraseRequest.evidence_bullets), not merely its id. Once a
    # Bullet is in hand its own `.id` is already the citable id (source_ids.py's
    # bullet_source_id() exists for a caller that has an EvidenceBullet but *doesn't* want to
    # materialize the full object — not this one).
    #
    # Bounds-checked, not just a dict lookup: a code-review pass found this would raise an
    # uncaught IndexError on a stale EvidenceBullet (e.g. match_report computed against a
    # profile snapshot that's since been edited) — silently violating generate_cv()'s own
    # docstring promise to never raise on anything but a genuine bug. A dangling reference is
    # skipped, matching matching/ranking.py's own select_bullets_within_budget(), which
    # guards this exact index for the same reason.
    histories_by_id = {history.id: history for history in profile.job_histories}
    resolved: list[Bullet] = []
    for item in evidence:
        history = histories_by_id.get(item.history_id)
        if history is None or item.bullet_index >= len(history.bullets):
            continue
        resolved.append(history.bullets[item.bullet_index])
    return resolved
