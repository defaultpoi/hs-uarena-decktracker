from hs_uarena_decktracker.models import ArenaRun, Card, DeckSnapshot


def snapshot(timestamp: str, count: int) -> DeckSnapshot:
    return DeckSnapshot(
        timestamp=timestamp,
        deck_id="1",
        cards=tuple(Card(str(index)) for index in range(count)),
    )


def test_current_deck_uses_latest_snapshot_even_when_incomplete():
    run = ArenaRun(
        deck_snapshots=[
            snapshot("12:00:00", 30),
            snapshot("12:01:00", 26),
        ]
    )

    assert run.current_deck is run.deck_snapshots[1]


def test_current_deck_uses_latest_snapshot_even_when_over_30_cards():
    run = ArenaRun(
        deck_snapshots=[
            snapshot("12:00:00", 30),
            snapshot("12:01:00", 35),
        ]
    )

    assert run.current_deck is run.deck_snapshots[1]


def test_current_deck_falls_back_to_partial_initial_draft():
    run = ArenaRun(deck_snapshots=[snapshot("12:00:00", 12)])

    assert run.current_deck is run.deck_snapshots[0]
