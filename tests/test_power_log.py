from hs_uarena_decktracker.power_log import count_losses


def test_counts_only_local_player_losses(tmp_path):
    power = tmp_path / "Power.log"
    power.write_text(
        """\
D 12:00:00.0000000 GameState.DebugPrintEntityChoices() - id=1 Player=Local#1234 TaskList=1 ChoiceType=MULLIGAN CountMin=0 CountMax=5
D 12:10:00.0000000 PowerTaskList.DebugPrintPower() - TAG_CHANGE Entity=Opponent#5678 tag=PLAYSTATE value=LOST
D 12:10:00.0000000 PowerTaskList.DebugPrintPower() - TAG_CHANGE Entity=Local#1234 tag=PLAYSTATE value=LOST
D 12:10:00.0000000 GameState.DebugPrintPower() - TAG_CHANGE Entity=Local#1234 tag=PLAYSTATE value=LOST
""",
        encoding="utf-8",
    )

    assert count_losses(power) == 1


def test_count_losses_requires_local_player_identity(tmp_path):
    power = tmp_path / "Power.log"
    power.write_text(
        "D 12:10:00.0000000 PowerTaskList.DebugPrintPower() - TAG_CHANGE Entity=Local#1234 tag=PLAYSTATE value=LOST\n",
        encoding="utf-8",
    )

    assert count_losses(power) == 0



def test_latest_result_ignores_losing_and_returns_terminal_state(tmp_path):
    power = tmp_path / "Power.log"
    power.write_text(
        "D 12:00:00.0000000 GameState.DebugPrintEntityChoices() - id=1 Player=Local#1234 TaskList=1 ChoiceType=MULLIGAN CountMin=0 CountMax=5\n"
        "D 12:10:00.0000000 PowerTaskList.DebugPrintPower() - TAG_CHANGE Entity=Local#1234 tag=PLAYSTATE value=LOSING\n"
        "D 12:11:00.0000000 PowerTaskList.DebugPrintPower() - TAG_CHANGE Entity=Local#1234 tag=PLAYSTATE value=WON\n",
        encoding="utf-8",
    )

    from hs_uarena_decktracker.power_log import latest_result
    assert latest_result(power) == "WON"
