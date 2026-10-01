from hs_uarena_decktracker.session import parse_sessions


def _arena(deck_id: str) -> str:
    return (
        f"D 12:00:00.0000000 DraftManager.OnChoicesAndContents - "
        f"Draft Deck ID: {deck_id}, Hero Card = HERO_11\n"
        f"D 12:00:00.0000000 DraftManager.OnChoicesAndContents - "
        "Draft deck contains card A\n"
    )


def _power(losses: int) -> str:
    lines = [
        "D 12:00:00.0000000 GameState.DebugPrintGame() - GameType=GT_UNDERGROUND_ARENA",
        "D 12:00:00.0000000 GameState.DebugPrintEntityChoices() - id=1 Player=Local#1234 TaskList=1 ChoiceType=MULLIGAN CountMin=0 CountMax=5",
    ]
    lines.extend(
        f"D 12:{10 + index:02d}:00.0000000 PowerTaskList.DebugPrintPower() - TAG_CHANGE Entity=Local#1234 tag=PLAYSTATE value=LOST"
        for index in range(losses)
    )
    return "\n".join(lines) + "\n"


def test_new_arena_run_resets_loss_count(tmp_path):
    first = tmp_path / "Hearthstone_2026_10_01_10_00_00"
    second = tmp_path / "Hearthstone_2026_10_01_11_00_00"
    first.mkdir()
    second.mkdir()

    (first / "Arena.log").write_text(_arena("old"), encoding="utf-8")
    (first / "Power.log").write_text(_power(3), encoding="utf-8")
    (second / "Arena.log").write_text(_arena("new"), encoding="utf-8")
    (second / "Power.log").write_text(_power(1), encoding="utf-8")

    run = parse_sessions([first, second])

    assert run.deck_id == "new"
    assert run.losses == 1
    assert run.run_ended is False
