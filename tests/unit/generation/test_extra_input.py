"""Criterion 17: per application, the user may supply extra input (a cover-note angle, an
achievement not yet in the profile, emphasis instructions). The user is prompted to promote
reusable additions into data/profile.yaml. Pure function — the actual YAML edit stays a
human/UI action (spec open question 3: YAML is the only write path)."""

from cv_writer.generation.extra_input import suggest_profile_promotions
from cv_writer.generation.models import ExtraInput, ExtraInputKind


def test_an_achievement_marked_as_a_promotion_candidate_is_suggested():
    inputs = [
        ExtraInput(
            id="extra-1",
            kind=ExtraInputKind.ACHIEVEMENT,
            text="Led the Q3 migration to a new payments provider.",
            promote_candidate=True,
        )
    ]

    suggestions = suggest_profile_promotions(inputs)

    assert len(suggestions) == 1
    assert suggestions[0].extra_input_id == "extra-1"


def test_an_achievement_not_marked_as_a_promotion_candidate_is_not_suggested():
    inputs = [
        ExtraInput(
            id="extra-1",
            kind=ExtraInputKind.ACHIEVEMENT,
            text="One-off detail, not reusable.",
            promote_candidate=False,
        )
    ]

    assert suggest_profile_promotions(inputs) == []


def test_cover_note_angle_and_emphasis_are_never_suggested_even_if_marked():
    inputs = [
        ExtraInput(
            id="extra-1",
            kind=ExtraInputKind.COVER_NOTE_ANGLE,
            text="Mention passion for climate tech.",
            promote_candidate=True,
        ),
        ExtraInput(
            id="extra-2",
            kind=ExtraInputKind.EMPHASIS,
            text="Emphasize backend depth over breadth.",
            promote_candidate=True,
        ),
    ]

    assert suggest_profile_promotions(inputs) == []
