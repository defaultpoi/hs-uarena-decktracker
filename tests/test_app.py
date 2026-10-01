from hs_uarena_decktracker.app import format_redraft
from hs_uarena_decktracker.models import Card, Redraft


def test_formats_complete_redraft_with_discarded_cards():
    redraft = Redraft(
        number=1,
        started_at="12:00:00",
        ended_at="12:01:00",
        selected=(
            Card("X", "New X"),
            Card("Y", "New Y"),
        ),
        discarded=(Card("A", "Old A"), Card("B", "Old B")),
        discarded_complete=True,
    )

    assert format_redraft(redraft) == (
        "#1  selected: New X, New Y  •  discarded: Old A, Old B"
    )


def test_formats_in_progress_redraft():
    redraft = Redraft(
        number=2,
        started_at="13:00:00",
        selected=(Card("X", "New X"),),
    )

    assert format_redraft(redraft) == "#2  IN PROGRESS  •  selected: New X"


def test_marks_partial_discard_information():
    redraft = Redraft(
        number=3,
        started_at="14:00:00",
        ended_at="14:01:00",
        selected=(Card("X", "New X"),),
        discarded=(Card("A", "Old A"),),
        discarded_complete=False,
    )

    assert format_redraft(redraft) == (
        "#3  selected: New X  •  discarded: Old A  •  partial"
    )
