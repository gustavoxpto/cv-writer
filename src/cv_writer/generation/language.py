"""Criteria 20-21: the CV is written in the posting's language, detected from the posting
text, shown to the user, overridable; generation is refused for a language not in the
profile's languages at working proficiency. PT-PT is a distinct target from PT-BR.

Curated stopword-frequency classifier — matches ADR 0003's already-established "curated
dictionaries + regex, no NLP/LLM" posture (ADR 0004 decision 8). There's no value detecting a
language outside what the tool would ever accept: criterion 20 refuses any language not
already in profile.languages regardless of how confidently it was detected, so this stays
deliberately narrow rather than growing into general-purpose language identification.
"""

from __future__ import annotations

import re

from pydantic import BaseModel

from cv_writer.ingestion.models import Posting
from cv_writer.ingestion.requirements import word_boundary_pattern
from cv_writer.profile.models import Profile
from cv_writer.profile.proficiency import WORKING_PROFICIENCY_LEVELS

from .pt_pt_checker import PtPtTermList, load_pt_pt_terms

# High-signal function words per language actually relevant here. Small and curated on
# purpose (ADR 0003's posture) — not exhaustive, just distinctive enough to separate the
# languages this tool will ever accept.
SUPPORTED_LANGUAGES: dict[str, set[str]] = {
    "english": {
        "the",
        "and",
        "with",
        "for",
        "our",
        "team",
        "experience",
        "you",
        "we",
        "are",
        "have",
        "will",
    },
    "portuguese": {
        "com",
        "para",
        "nossa",
        "nosso",
        "equipa",
        "equipe",
        "experiência",
        "você",
        "somos",
        "temos",
        "candidato",
        "vaga",
    },
    "german": {
        "und",
        "der",
        "die",
        "das",
        "wir",
        "mit",
        "für",
        "erfahrung",
        "team",
        "suchen",
        "unser",
    },
}

# Minimum "working" proficiency rank (criterion 20's floor) — anything below this refuses
# generation in that language, even if the language is in the profile at all.
#
# WORKING_PROFICIENCY_LEVELS is shared with matching/matcher.py (profile/proficiency.py) —
# a code-review pass found the two packages had quietly drifted into two different
# vocabularies for the same Language.proficiency field (matcher.py recognized "advanced"/
# "c1"/"c2" as working-proficiency-or-above; this module didn't), so matching could say a
# language requirement was MATCHED while generation refused to write in that language for
# the same profile. One shared set now backs both.
_BELOW_WORKING_RANK: dict[str, int] = {"basic": 1, "conversational": 2}
MINIMUM_WORKING_RANK = 3


def _proficiency_rank(proficiency: str) -> int:
    normalized = proficiency.strip().lower()
    if normalized in WORKING_PROFICIENCY_LEVELS:
        return MINIMUM_WORKING_RANK
    return _BELOW_WORKING_RANK.get(normalized, 0)

# Portugal/Angola/Mozambique/... -> pt-pt; Brazil -> pt-br. Small and curated (ADR 0004
# decision 8) — not an exhaustive list of every Portuguese-speaking country.
_COUNTRY_TO_VARIANT: dict[str, str] = {
    "brazil": "pt-br",
    "brasil": "pt-br",
    "portugal": "pt-pt",
    "angola": "pt-pt",
    "mozambique": "pt-pt",
    "moçambique": "pt-pt",
    "cape verde": "pt-pt",
}

_WORD_PATTERN = re.compile(r"\w+", re.UNICODE)


class LanguageDetection(BaseModel):
    """What language a posting's text looks like, and how confident that guess is."""

    language: str
    confidence: str  # "high" | "low"


class LanguageResolution(BaseModel):
    """The final language decision for one generation run (criteria 20-21)."""

    detected: str
    variant: str | None
    allowed: bool
    reason: str | None = None


def detect_posting_language(raw_text: str) -> LanguageDetection:
    """Count stopword hits per supported language and pick the highest scorer. A near-tie or
    zero hits returns low confidence rather than guessing."""
    words = {w.lower() for w in _WORD_PATTERN.findall(raw_text)}

    scores = {
        language: len(words & stopwords) for language, stopwords in SUPPORTED_LANGUAGES.items()
    }
    best_language = max(scores, key=lambda lang: scores[lang])
    best_score = scores[best_language]

    if best_score == 0:
        return LanguageDetection(language="unknown", confidence="low")

    runner_up_score = max((s for lang, s in scores.items() if lang != best_language), default=0)
    confidence = "high" if best_score > runner_up_score else "low"
    return LanguageDetection(language=best_language, confidence=confidence)


def resolve_output_language(
    posting: Posting,
    profile: Profile,
    override: str | None = None,
    *,
    pt_terms: PtPtTermList | None = None,
) -> LanguageResolution:
    """Resolve the language (and PT-PT/PT-BR variant, if applicable) to generate in, and
    whether the profile actually supports it at working proficiency (criterion 20).

    `pt_terms` lets a caller that already loaded the PT-PT term list (e.g. pipeline.py, which
    also needs it for check_pt_pt()) pass it straight through instead of this function loading
    its own copy from disk a second time for the same request — defaults to loading it here
    when the caller has no reason to load it early.
    """
    if override is not None:
        # Normalize case: detect_posting_language() always returns a lowercase language
        # name, and every profile.languages entry / test fixture in this repo stores the
        # natural capitalized form ("English", "Portuguese") — a code-review pass found that
        # passing that exact, natural value back as an override broke the profile-support
        # lookup below purely on case.
        language = override.strip().lower()
    else:
        language = detect_posting_language(posting.raw_text).language

    variant = _resolve_pt_variant(posting, pt_terms) if language == "portuguese" else None

    allowed, reason = _check_profile_supports(language, profile)
    return LanguageResolution(detected=language, variant=variant, allowed=allowed, reason=reason)


def _resolve_pt_variant(posting: Posting, pt_terms: PtPtTermList | None) -> str | None:
    if posting.country:
        mapped = _COUNTRY_TO_VARIANT.get(posting.country.strip().lower())
        if mapped is not None:
            return mapped

    # No country, or an unmapped one: fall back to the BR-lexis signal the PT-PT checker
    # already curates (criterion 21) — reusing one data file for a second purpose rather
    # than maintaining a parallel list.
    terms = pt_terms if pt_terms is not None else load_pt_pt_terms()
    lexis_entries = [entry for entry in terms.entries if entry.category == "lexis"]
    for entry in lexis_entries:
        if entry.is_regex:
            continue  # this signal only checks simple literal lexis, not regex patterns
        if word_boundary_pattern(entry.pattern).search(posting.raw_text):
            return "pt-br"

    return None  # genuinely ambiguous — surfaced to the user, never guessed (criterion 20)


def _check_profile_supports(language: str, profile: Profile) -> tuple[bool, str | None]:
    for profile_language in profile.languages:
        if profile_language.name.strip().lower() != language:
            continue
        rank = _proficiency_rank(profile_language.proficiency)
        if rank >= MINIMUM_WORKING_RANK:
            return True, None
        return False, (
            f"'{language}' is in the profile only at '{profile_language.proficiency}' "
            "proficiency, below the working-proficiency floor (criterion 20)"
        )

    return False, f"'{language}' is not listed in the profile's languages (criterion 20)"
