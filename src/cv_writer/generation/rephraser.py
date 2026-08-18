"""Criteria 18, 22, 23: the LLM's role is bounded to rephrasing and ordering selected
evidence for the posting's language and emphasis. The call sits behind one interface
(`Rephraser`) that tests replace with `FakeRephraser` — the whole pipeline is testable
offline, no API key, no network. The real implementation (`ClaudeRephraser`) reads
`ANTHROPIC_API_KEY` from the environment only inside `rephrase()`, at call time, never
storing it on `self` or writing it anywhere (criterion 23, docs/security.md).

Uses the Claude API's structured outputs (`client.messages.parse(output_format=...)`) so the
LLM's response is schema-validated into `RephraseOutput` directly — every bullet is
*structurally* forced to carry a `source_id`, though `generation/validator.py` still
independently re-checks that id is real and its claims check out; the LLM's own citation is
never trusted on its say-so alone.
"""

from __future__ import annotations

from typing import Protocol

from pydantic import BaseModel

from cv_writer.profile.models import Bullet

from .models import ExtraInput, RephraseOutput

DEFAULT_MODEL = "claude-opus-5"


class RephraseRequest(BaseModel):
    """Everything the Rephraser needs to produce bounded, citable output: the selected
    evidence (profile bullets + per-application extra input), the target language/variant
    (criteria 20-21), and the posting text for emphasis context."""

    evidence_bullets: list[Bullet]
    extra_inputs: list[ExtraInput]
    target_language: str
    target_variant: str | None
    posting_text: str


class Rephraser(Protocol):
    """The one interface the LLM sits behind (criterion 22)."""

    def rephrase(self, request: RephraseRequest) -> RephraseOutput: ...


class FakeRephraser:
    """Deterministic, no-network test double (criterion 22).

    Default behavior echoes each evidence bullet's own `result` text and each extra input's
    own text as "generated" bullets citing their real source ids — a trivial but truthful
    transformation, useful for pipeline happy-path tests without hand-crafting an expected
    LLM response every time. Pass `fixed_response` to return an arbitrary canned
    `RephraseOutput` instead (including a deliberately fabricated one, for testing that the
    validator actually catches it).
    """

    def __init__(self, fixed_response: RephraseOutput | None = None):
        self._fixed_response = fixed_response

    def rephrase(self, request: RephraseRequest) -> RephraseOutput:
        if self._fixed_response is not None:
            return self._fixed_response

        from .models import GeneratedBulletDraft

        bullets = [
            GeneratedBulletDraft(text=bullet.result, source_id=bullet.id)
            for bullet in request.evidence_bullets
        ]
        bullets += [
            GeneratedBulletDraft(text=extra.text, source_id=extra.id)
            for extra in request.extra_inputs
        ]
        return RephraseOutput(bullets=bullets)


class ClaudeRephraser:
    """The real Rephraser, behind the Claude API's structured outputs. Never used in this
    repo's automated tests (criterion 22) — exercised only by a human running the pipeline
    for real, with a real ANTHROPIC_API_KEY set in their own environment."""

    def __init__(self, model: str = DEFAULT_MODEL):
        self._model = model

    def rephrase(self, request: RephraseRequest) -> RephraseOutput:
        import anthropic

        # Reads ANTHROPIC_API_KEY from the environment at call time only (criterion 23) —
        # never stored on self, never logged, never written to disk/DB/artifact.
        client = anthropic.Anthropic()
        response = client.messages.parse(
            model=self._model,
            max_tokens=4096,
            messages=[{"role": "user", "content": _build_prompt(request)}],
            output_format=RephraseOutput,
        )
        return response.parsed_output


def _build_prompt(request: RephraseRequest) -> str:
    """Bound the LLM to rephrasing and ordering only (criterion 18) — it is explicitly told
    not to invent facts, and every piece of evidence it's given already carries its own
    citable id, which it's instructed to echo back on the bullet derived from it."""
    evidence_lines = [
        f"- id={bullet.id}: situation={bullet.situation!r} task={bullet.task!r} "
        f"action={bullet.action!r} result={bullet.result!r} "
        f"metric={bullet.metric.model_dump() if bullet.metric else None}"
        for bullet in request.evidence_bullets
    ]
    extra_lines = [
        f"- id={extra.id}: kind={extra.kind.value} text={extra.text!r}"
        for extra in request.extra_inputs
    ]
    variant_note = f" ({request.target_variant})" if request.target_variant else ""

    return (
        "You are rephrasing and reordering pre-selected CV evidence for a job posting. "
        "You must NOT invent, embellish, or add any fact, employer, title, date, credential, "
        "or number not already present in the evidence below — your only job is wording and "
        f"order, in {request.target_language}{variant_note}. Every bullet you produce must "
        "set source_id to the exact id of the evidence item it came from.\n\n"
        f"Posting text (for emphasis context only):\n{request.posting_text}\n\n"
        f"Evidence bullets:\n" + "\n".join(evidence_lines) + "\n\n"
        "Extra input:\n" + ("\n".join(extra_lines) if extra_lines else "(none)")
    )
