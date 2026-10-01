from hs_uarena_decktracker.session import parse_session, parse_sessions


def test_only_marks_underground_when_power_log_says_so(tmp_path):
    (tmp_path / "Arena.log").write_text(
        "D 13:00:00.0000000 DraftManager.OnChoicesAndContents - Draft Deck ID: 1, Hero Card = HERO_1\n",
        encoding="utf-8",
    )
    (tmp_path / "Power.log").write_text(
        "GameState.DebugPrintGame() - GameType=GT_UNDERGROUND_ARENA\n",
        encoding="utf-8",
    )

    run = parse_session(tmp_path)
    assert run.underground is True


def test_combines_matching_deck_across_sessions(tmp_path):
    first = tmp_path / "Hearthstone_2026_10_01_11_56_04"
    second = tmp_path / "Hearthstone_2026_10_01_13_22_39"
    first.mkdir()
    second.mkdir()

    first_log = """\
D 12:00:00.0000000 DraftManager.OnChoicesAndContents - Draft Deck ID: 99, Hero Card = HERO_11
D 12:00:00.0000000 DraftManager.OnChoicesAndContents - Draft deck contains card A
D 12:00:00.0000000 DraftManager.OnChoicesAndContents - Draft deck contains card B
D 12:00:00.0000000 DraftManager.OnChoicesAndContents - Draft deck contains card C
D 12:01:00.0000000 SetDraftMode - REDRAFTING
D 12:01:01.0000000 Client chooses: X (X)
D 12:01:02.0000000 Client chooses: Y (Y)
D 12:01:03.0000000 Client chooses: Z (Z)
D 12:01:04.0000000 Client chooses: Q (Q)
D 12:01:05.0000000 Client chooses: W (W)
D 12:01:06.0000000 SetDraftMode - ACTIVE_DRAFT_DECK
D 12:02:00.0000000 DraftManager.OnChoicesAndContents - Draft Deck ID: 99, Hero Card = HERO_11
D 12:02:00.0000000 DraftManager.OnChoicesAndContents - Draft deck contains card B
D 12:02:00.0000000 DraftManager.OnChoicesAndContents - Draft deck contains card C
D 12:02:00.0000000 DraftManager.OnChoicesAndContents - Draft deck contains card X
"""
    first.joinpath("Arena.log").write_text(first_log, encoding="utf-8")

    second_log = """\
D 13:00:00.0000000 DraftManager.OnChoicesAndContents - Draft Deck ID: 99, Hero Card = HERO_11
D 13:00:00.0000000 DraftManager.OnChoicesAndContents - Draft deck contains card B
D 13:00:00.0000000 DraftManager.OnChoicesAndContents - Draft deck contains card C
D 13:00:00.0000000 DraftManager.OnChoicesAndContents - Draft deck contains card X
D 13:01:00.0000000 SetDraftMode - REDRAFTING
D 13:01:01.0000000 Client chooses: B (B)
D 13:01:02.0000000 Client chooses: C (C)
D 13:01:03.0000000 Client chooses: R (R)
D 13:01:04.0000000 Client chooses: S (S)
D 13:01:05.0000000 Client chooses: T (T)
D 13:01:06.0000000 SetDraftMode - ACTIVE_DRAFT_DECK
D 13:02:00.0000000 DraftManager.OnChoicesAndContents - Draft Deck ID: 99, Hero Card = HERO_11
D 13:02:00.0000000 DraftManager.OnChoicesAndContents - Draft deck contains card B
D 13:02:00.0000000 DraftManager.OnChoicesAndContents - Draft deck contains card X
D 13:02:00.0000000 DraftManager.OnChoicesAndContents - Draft deck contains card R
"""
    second.joinpath("Arena.log").write_text(second_log, encoding="utf-8")

    run = parse_sessions([first, second])

    assert run.deck_id == "99"
    assert len(run.redrafts) == 2
    assert [card.card_id for card in run.redrafts[0].selected] == ["X", "Y", "Z", "Q", "W"]
    assert [card.card_id for card in run.redrafts[1].selected] == ["B", "C", "R", "S", "T"]
