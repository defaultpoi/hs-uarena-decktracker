from hs_uarena_decktracker.app import format_deck, format_redraft, log_fingerprint, redraft_state
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


def test_log_fingerprint_changes_when_log_is_updated(tmp_path):
    session = tmp_path / "Hearthstone_2026_10_01_12_00_00"
    session.mkdir()
    arena_log = session / "Arena.log"
    power_log = session / "Power.log"
    arena_log.write_text("first")
    power_log.write_text("power")

    first = log_fingerprint([session])
    arena_log.write_text("second update")
    second = log_fingerprint([session])

    assert first != second


def test_log_fingerprint_includes_multiple_sessions(tmp_path):
    first = tmp_path / "Hearthstone_2026_10_01_12_00_00"
    second = tmp_path / "Hearthstone_2026_10_01_13_00_00"
    first.mkdir()
    second.mkdir()
    (first / "Arena.log").write_text("first")
    (second / "Arena.log").write_text("second")

    fingerprint = log_fingerprint([first, second])

    assert len(fingerprint) == 4
    assert {entry[0] for entry in fingerprint} == {
        str(first / "Arena.log"),
        str(first / "Power.log"),
        str(second / "Arena.log"),
        str(second / "Power.log"),
    }


def test_formats_deck_compactly_with_counts():
    cards = (
        Card("A", "Arcane Bolt"),
        Card("B", "Fireball"),
        Card("A", "Arcane Bolt"),
        Card("C", "Unknown Card"),
    )

    assert format_deck(cards) == (
        "Arcane Bolt ×2\n"
        "Fireball\n"
        "Unknown Card"
    )


def test_formats_active_redraft_state():
    redraft = Redraft(
        number=2,
        started_at="13:00:00",
        selected=(Card("X", "New X"), Card("Y", "New Y")),
    )

    assert redraft_state(redraft) == (
        "REDRAFT #2 — IN PROGRESS\n"
        "Selected: New X, New Y"
    )


def test_formats_completed_redraft_state():
    redraft = Redraft(
        number=1,
        started_at="12:00:00",
        ended_at="12:01:00",
        selected=(Card("X", "New X"),),
        discarded=(Card("A", "Old A"),),
        discarded_complete=True,
    )

    assert redraft_state(redraft) == (
        "REDRAFT #1\n"
        "Selected: New X\n"
        "Discarded (complete): Old A"
    )
