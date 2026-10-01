from hs_uarena_decktracker.session import parse_session


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
