from collections import Counter

from hs_uarena_decktracker.arena_log import ArenaLogParser


def deck_lines(timestamp: str, cards: list[str]) -> list[str]:
    lines = [
        f"D {timestamp} DraftManager.OnChoicesAndContents - Draft Deck ID: 1, Hero Card = HERO_11"
    ]
    lines.extend(
        f"D {timestamp} DraftManager.OnChoicesAndContents - Draft deck contains card {card}"
        for card in cards
    )
    return lines


def test_realistic_two_redraft_flow_across_sessions(tmp_path):
    # Thirty-card starting deck with a duplicate A. Redraft #1 replaces
    # four old cards while one newly selected card (W) is itself discarded.
    initial = list("AABCDEFGHIJKLMNOPQRSTUVWXY")  # 27 cards
    initial += ["Z", "AA", "AB"]
    assert len(initial) == 30
    assert Counter(initial)["A"] == 2

    first_result = [card for card in initial if card not in {"B", "D", "E", "J"}]
    first_result += ["X", "Y", "Z", "Q"]
    assert len(first_result) == 30

    later_gameplay = first_result + ["EXTRA_1", "EXTRA_2"]
    assert len(later_gameplay) == 32

    first_lines = deck_lines("12:00:00.0000000", initial)
    first_lines += [
        "D 12:01:00.0000000 SetDraftMode - REDRAFTING",
        "D 12:01:00.1000000 DraftManager.OnRedraftBegin - Got new redraft deck with ID: 100",
        "D 12:01:01.0000000 Client chooses: X (X)",
        "D 12:01:02.0000000 Client chooses: Y (Y)",
        "D 12:01:03.0000000 Client chooses: Z (Z)",
        "D 12:01:04.0000000 Client chooses: Q (Q)",
        "D 12:01:05.0000000 Client chooses: W (W)",
        "D 12:01:06.0000000 SetDraftMode - ACTIVE_DRAFT_DECK",
    ]
    first_lines += deck_lines("12:02:00.0000000", first_result)
    # This later mutation must not affect redraft #1 discard inference.
    first_lines += deck_lines("12:03:00.0000000", later_gameplay)

    second_before = later_gameplay
    second_result = [card for index, card in enumerate(second_before) if index not in {0, 1, 2, 3, 4}]
    second_result += ["R", "S", "T", "U", "V"]
    assert len(second_result) == 32

    second_lines = [
        "D 13:00:00.0000000 SetDraftMode - REDRAFTING",
        "D 13:00:00.1000000 DraftManager.OnRedraftBegin - Got new redraft deck with ID: 200",
        "D 13:00:01.0000000 Client chooses: R (R)",
        "D 13:00:02.0000000 Client chooses: S (S)",
        "D 13:00:03.0000000 Client chooses: T (T)",
        "D 13:00:04.0000000 Client chooses: U (U)",
        "D 13:00:05.0000000 Client chooses: V (V)",
        "D 13:00:06.0000000 SetDraftMode - ACTIVE_DRAFT_DECK",
    ]
    second_lines += deck_lines("13:01:00.0000000", second_result)

    first = tmp_path / "Hearthstone_2026_10_01_12_00_00"
    second = tmp_path / "Hearthstone_2026_10_01_13_00_00"
    first.mkdir()
    second.mkdir()
    (first / "Arena.log").write_text("\n".join(first_lines), encoding="utf-8")
    (second / "Arena.log").write_text("\n".join(second_lines), encoding="utf-8")

    run = ArenaLogParser().parse_many([first / "Arena.log", second / "Arena.log"])

    assert len(run.redrafts) == 2
    assert [r.redraft_deck_id for r in run.redrafts] == ["100", "200"]

    first_discarded = [card.card_id for card in run.redrafts[0].discarded]
    assert first_discarded == ["B", "D", "E", "J", "W"]
    assert run.redrafts[0].discarded_complete is True
    assert any(card.card_id == "W" and card.name == "W" for card in run.redrafts[0].discarded)

    second_discarded = Counter(card.card_id for card in run.redrafts[1].discarded)
    assert sum(second_discarded.values()) == 5
    assert run.redrafts[1].discarded_complete is True
