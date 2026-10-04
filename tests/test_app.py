from hs_uarena_decktracker.app import (
    format_deck,
    format_redraft,
    format_run_progress,
    format_run_status,
    log_fingerprint,
    redraft_state,
)
from hs_uarena_decktracker.models import ArenaRun, Card, GeneratedDeckCard, Redraft


def test_formats_complete_redraft_with_discarded_cards():
    redraft = Redraft(
        number=1,
        started_at="12:00:00",
        ended_at="12:01:00",
        selected=(Card("X", "New X"), Card("Y", "New Y")),
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


def test_formats_deck_using_known_name_for_duplicate_card_ids():
    cards = (
        Card("A", None),
        Card("A", "Arcane Bolt"),
        Card("B", "Fireball"),
    )

    assert format_deck(cards) == (
        "Arcane Bolt ×2\n"
        "Fireball"
    )


def test_formats_active_redraft_state():
    redraft = Redraft(
        number=2,
        started_at="13:00:00",
        selected=(Card("X", "New X"), Card("Y", "New Y")),
    )

    assert redraft_state(redraft) == (
        "REDRAFT #2 — IN PROGRESS\n"
        "Selected (2/5): New X, New Y\n"
        "Discarded: waiting for resulting deck"
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
        "Selected (1/5): New X\n"
        "Discarded (1/5, complete): Old A"
    )


def test_formats_compact_run_status():
    run = ArenaRun(underground=True, losses=1, last_result="WON", hero_card_id="HERO_11")

    assert format_run_status(run, 30) == (
        "UNDERGROUND ARENA  •  1/3 losses\n"
        "30 cards  •  Last: WON  •  Hero: HERO_11"
    )


def test_formats_completed_run_status():
    run = ArenaRun(underground=True, losses=3, last_result="LOST", hero_card_id="HERO_11")

    assert format_run_status(run, 28) == (
        "UNDERGROUND ARENA  •  RUN COMPLETE\n"
        "28 cards  •  Last: LOST  •  Hero: HERO_11"
    )


def test_formats_run_progress_after_intervening_win():
    from hs_uarena_decktracker.models import ArenaRun

    run = ArenaRun(
        game_results=["LOST", "WON", "LOST"],
        redrafts=[
            Redraft(number=1, started_at="12:00:00", selected=()),
            Redraft(number=2, started_at="13:00:00", selected=()),
        ],
    )

    assert format_run_progress(run) == (
        "GAME #1: LOST\n"
        "  ↳ REDRAFT #1\n"
        "GAME #2: WON\n"
        "GAME #3: LOST\n"
        "  ↳ REDRAFT #2"
    )


def test_formats_run_progress_without_inventing_timestamps():
    run = ArenaRun(
        game_results=["LOST", "WON", "LOST", "LOST"],
        redrafts=[
            Redraft(number=1, started_at="12:00:00", selected=()),
            Redraft(number=2, started_at="13:00:00", selected=()),
        ],
    )

    assert format_run_progress(run) == (
        "GAME #1: LOST\n"
        "  ↳ REDRAFT #1\n"
        "GAME #2: WON\n"
        "GAME #3: LOST\n"
        "  ↳ REDRAFT #2\n"
        "GAME #4: LOST\n"
        "RUN COMPLETE"
    )


def test_formats_deck_effects_grouped_by_trigger_and_source():
    effects = [
        GeneratedDeckCard(
            card=Card("BT_123", "Kargath Bladefist"),
            source_card=Card("JAIL_384", "Chainbreaker Hogger"),
            trigger="START_OF_GAME",
            event="CREATED_IN_DECK",
            reason="Start of Game effect copied this card into the deck",
        ),
        GeneratedDeckCard(
            card=Card("BAR_721t", "Olgra, Mankrik's Wife"),
            source_card=Card("BAR_721", "Mankrik"),
            trigger="CARD_EFFECT",
            event="CREATED_IN_DECK",
            reason="Card effect created this card in the deck",
        ),
    ]

    from hs_uarena_decktracker.app import format_deck_effects

    assert format_deck_effects(effects) == (
        "START OF GAME\n"
        "Chainbreaker Hogger\n"
        "  + Kargath Bladefist\n"
        "CARD EFFECT\n"
        "Mankrik\n"
        "  + Olgra, Mankrik's Wife"
    )


def test_format_deck_effects_empty():
    from hs_uarena_decktracker.app import format_deck_effects

    assert format_deck_effects([]) == "No generated deck effects detected"
