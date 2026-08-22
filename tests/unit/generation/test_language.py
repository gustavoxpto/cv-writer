"""Criteria 20-21: the CV is written in the posting's language, detected from the posting
text, shown to the user, overridable; generation is refused for a language not in the
profile's languages at working proficiency. PT-PT is a distinct target from PT-BR. See ADR
0004 decision 8 for the curated stopword-frequency approach (no NLP/LLM) and the PT-PT/PT-BR
resolution order (country, then a reused BR-lexis signal, then an explicit unresolved case).
"""

from datetime import datetime, timezone

import pytest

from cv_writer.generation.language import (
    LanguageRefusal,
    detect_posting_language,
    resolve_output_language,
)
from cv_writer.ingestion.models import Posting
from cv_writer.profile.models import Identity, Language, Profile

ENGLISH_POSTING = (
    "We are looking for a senior backend engineer to join our team. The ideal candidate "
    "has experience with Python and distributed systems, and enjoys solving hard problems."
)
PORTUGUESE_POSTING = (
    "Procuramos um engenheiro backend sénior para se juntar à nossa equipa. O candidato "
    "ideal tem experiência com Python e sistemas distribuídos."
)


def _posting(raw_text: str, *, country: str | None = None) -> Posting:
    return Posting(
        raw_text=raw_text,
        source="https://example.com/job",
        fetched_at=datetime.now(timezone.utc),
        ingestion_tier=1,
        country=country,
    )


@pytest.fixture
def profile_en_pt() -> Profile:
    return Profile(
        identity=Identity(name="Ana Example", email="ana@example.com"),
        languages=[
            Language(name="English", proficiency="professional"),
            Language(name="Portuguese", proficiency="native"),
            Language(name="German", proficiency="basic"),
        ],
    )


def test_english_posting_detected_as_english_with_high_confidence():
    detection = detect_posting_language(ENGLISH_POSTING)

    assert detection.language == "english"
    assert detection.confidence == "high"


def test_portuguese_posting_with_brazil_country_resolves_to_pt_br(profile_en_pt):
    posting = _posting(PORTUGUESE_POSTING, country="Brazil")

    resolution = resolve_output_language(posting, profile_en_pt)

    assert resolution.detected == "portuguese"
    assert resolution.variant == "pt-br"


def test_portuguese_posting_with_portugal_country_resolves_to_pt_pt(profile_en_pt):
    posting = _posting(PORTUGUESE_POSTING, country="Portugal")

    resolution = resolve_output_language(posting, profile_en_pt)

    assert resolution.detected == "portuguese"
    assert resolution.variant == "pt-pt"


def test_portuguese_posting_with_no_country_falls_back_to_br_lexis_signal(profile_en_pt):
    posting = _posting("Vaga para gerenciar o time de vendas.")  # BR lexis, no country given

    resolution = resolve_output_language(posting, profile_en_pt)

    assert resolution.variant == "pt-br"


def test_portuguese_posting_with_no_signal_at_all_is_unresolved(profile_en_pt):
    posting = _posting(PORTUGUESE_POSTING)  # no country, no BR-lexis markers

    resolution = resolve_output_language(posting, profile_en_pt)

    assert resolution.variant is None


def test_detected_language_absent_from_profile_is_refused(profile_en_pt):
    posting = _posting("Wir suchen einen erfahrenen Softwareentwickler fuer unser Team.")

    resolution = resolve_output_language(posting, profile_en_pt)

    assert resolution.allowed is False
    assert resolution.reason is not None


def test_detected_language_below_working_proficiency_is_refused(profile_en_pt):
    german_posting = _posting("Wir suchen einen Softwareentwickler mit Python-Erfahrung.")

    # Force the detected language to "german" via override, since German is in the profile
    # but only at "basic" proficiency — below the working-proficiency floor criterion 20 sets.
    resolution = resolve_output_language(german_posting, profile_en_pt, override="german")

    assert resolution.allowed is False


def test_reason_code_is_not_in_profile_for_a_supported_language_missing_from_the_profile():
    # German is in SUPPORTED_LANGUAGES, so this stays green once T-003 puts the
    # SUPPORTED_LANGUAGES gate ahead of the profile check — only the profile-membership
    # cause can fire here.
    profile = Profile(
        identity=Identity(name="Ana Example", email="ana@example.com"),
        languages=[Language(name="English", proficiency="professional")],
    )
    posting = _posting(ENGLISH_POSTING)

    resolution = resolve_output_language(posting, profile, override="german")

    assert resolution.allowed is False
    assert resolution.reason_code == LanguageRefusal.NOT_IN_PROFILE


def test_reason_code_is_below_working_proficiency_for_german_at_basic(profile_en_pt):
    # profile_en_pt lists German at "basic" — in the profile, but below the working floor.
    posting = _posting(ENGLISH_POSTING)

    resolution = resolve_output_language(posting, profile_en_pt, override="german")

    assert resolution.allowed is False
    assert resolution.reason_code == LanguageRefusal.BELOW_WORKING_PROFICIENCY


def test_english_posting_is_allowed_at_professional_proficiency(profile_en_pt):
    posting = _posting(ENGLISH_POSTING)

    resolution = resolve_output_language(posting, profile_en_pt)

    assert resolution.detected == "english"
    assert resolution.allowed is True


def test_override_takes_precedence_over_detection(profile_en_pt):
    posting = _posting(ENGLISH_POSTING)

    resolution = resolve_output_language(posting, profile_en_pt, override="portuguese")

    assert resolution.detected == "portuguese"


def test_override_is_case_normalized_against_the_profiles_capitalized_language_names(
    profile_en_pt,
):
    # Regression: passing the override in its natural capitalized form (exactly how every
    # profile.languages entry in this repo stores it, e.g. "English") used to fail the
    # profile-support lookup purely because detect_posting_language() always returns
    # lowercase and the two were compared case-sensitively.
    posting = _posting(ENGLISH_POSTING)

    resolution = resolve_output_language(posting, profile_en_pt, override="English")

    assert resolution.allowed is True


def test_a_proficiency_level_recognized_by_matching_is_also_recognized_by_generation(
    profile_en_pt,
):
    # Regression: matching/matcher.py's working-proficiency vocabulary included "advanced"/
    # "c1"/"c2"; this module's used to be a separate, narrower list that didn't — so matching
    # could report a language requirement MATCHED while generation refused it for the same
    # profile. Both now share profile/proficiency.py's WORKING_PROFICIENCY_LEVELS.
    from cv_writer.profile.models import Identity, Language, Profile

    profile = Profile(
        identity=Identity(name="Ana Example", email="ana@example.com"),
        languages=[Language(name="German", proficiency="advanced")],
    )
    posting = _posting("Wir suchen.")

    resolution = resolve_output_language(posting, profile, override="german")

    assert resolution.allowed is True
