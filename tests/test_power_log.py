from hs_uarena_decktracker.power_log import count_losses, game_results


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


def test_game_results_preserves_terminal_results_in_order(tmp_path):
    power = tmp_path / "Power.log"
    power.write_text(
        "D 12:00:00.0000000 GameState.DebugPrintEntityChoices() - id=1 Player=Local#1234 TaskList=1 ChoiceType=MULLIGAN CountMin=0 CountMax=5\n"
        "D 12:10:00.0000000 PowerTaskList.DebugPrintPower() - TAG_CHANGE Entity=Local#1234 tag=PLAYSTATE value=LOST\n"
        "D 12:20:00.0000000 PowerTaskList.DebugPrintPower() - TAG_CHANGE Entity=Local#1234 tag=PLAYSTATE value=WON\n"
        "D 12:30:00.0000000 PowerTaskList.DebugPrintPower() - TAG_CHANGE Entity=Local#1234 tag=PLAYSTATE value=LOSING\n",
        encoding="utf-8",
    )

    assert game_results(power) == ["LOST", "WON"]


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



def test_game_results_skips_unknown_human_player_placeholder(tmp_path):
    power = tmp_path / "Power.log"
    power.write_text(
        "D 05:24:08.8438472 GameState.DebugPrintEntityChoices() - id=1 Player=UNKNOWN HUMAN PLAYER TaskList=6 ChoiceType=MULLIGAN CountMin=0 CountMax=5\n"
        "D 05:24:08.8948475 GameState.DebugPrintEntityChoices() - id=2 Player=Korp#21551 TaskList=7 ChoiceType=MULLIGAN CountMin=0 CountMax=3\n"
        "D 05:37:21.0195390 PowerTaskList.DebugPrintPower() - TAG_CHANGE Entity=Korp#21551 tag=PLAYSTATE value=WON\n"
        "D 05:50:17.0786205 PowerTaskList.DebugPrintPower() - TAG_CHANGE Entity=Korp#21551 tag=PLAYSTATE value=WON\n"
        "D 06:14:37.2059474 PowerTaskList.DebugPrintPower() - TAG_CHANGE Entity=Korp#21551 tag=PLAYSTATE value=CONCEDED\n"
        "D 06:14:37.2059474 PowerTaskList.DebugPrintPower() - TAG_CHANGE Entity=Korp#21551 tag=PLAYSTATE value=LOST\n"
        "D 06:35:55.7160100 PowerTaskList.DebugPrintPower() - TAG_CHANGE Entity=Korp#21551 tag=PLAYSTATE value=LOSING\n"
        "D 06:35:55.7700107 PowerTaskList.DebugPrintPower() - TAG_CHANGE Entity=Korp#21551 tag=PLAYSTATE value=LOST\n"
        "D 06:46:50.4681186 PowerTaskList.DebugPrintPower() - TAG_CHANGE Entity=Korp#21551 tag=PLAYSTATE value=WON\n"
        "D 06:56:54.9085548 PowerTaskList.DebugPrintPower() - TAG_CHANGE Entity=Korp#21551 tag=PLAYSTATE value=LOSING\n"
        "D 06:56:55.8545680 PowerTaskList.DebugPrintPower() - TAG_CHANGE Entity=Korp#21551 tag=PLAYSTATE value=LOST\n",
        encoding="utf-8",
    )

    assert game_results(power) == ["WON", "WON", "LOST", "LOST", "WON", "LOST"]
    assert count_losses(power) == 3


def test_latest_start_of_game_duplicates(tmp_path):
    power = tmp_path / "Power.log"
    power.write_text(
        """
D 01:00:00.0000000 PowerTaskList.DebugPrintPower() - BLOCK_START BlockType=TRIGGER Entity=[entityName=Chainbreaker Hogger id=14 zone=DECK zonePos=0 cardId=JAIL_384 player=1] EffectCardId=x EffectIndex=1 Target=0 SubOption=-1 TriggerKeyword=START_OF_GAME_KEYWORD
D 01:00:00.0000000 PowerTaskList.DebugPrintPower() -     SHOW_ENTITY - Updating Entity=[entityName=UNKNOWN ENTITY [cardType=INVALID] id=72 zone=DECK zonePos=0 cardId= player=1] CardID=BT_123
D 01:00:00.0000000 PowerTaskList.DebugPrintPower() -         tag=CREATOR value=14
D 01:00:00.0000000 PowerTaskList.DebugPrintPower() -         tag=COPIED_FROM_ENTITY_ID value=33
D 01:00:00.0000000 PowerTaskList.DebugPrintPower() -     SHOW_ENTITY - Updating Entity=[entityName=UNKNOWN ENTITY [cardType=INVALID] id=73 zone=DECK zonePos=0 cardId= player=1] CardID=BAR_721
D 01:00:00.0000000 PowerTaskList.DebugPrintPower() -         tag=CREATOR value=14
D 01:00:00.0000000 PowerTaskList.DebugPrintPower() -         tag=COPIED_FROM_ENTITY_ID value=13
D 01:00:00.0000000 PowerTaskList.DebugPrintPower() -     BLOCK_END
D 01:00:01.0000000 PowerTaskList.DebugPrintPower() - TAG_CHANGE Entity=[entityName=Kargath Bladefist id=72 zone=DECK zonePos=0 cardId=BT_123 player=1] tag=ZONE value=DECK
D 01:00:01.0000000 PowerTaskList.DebugPrintPower() - TAG_CHANGE Entity=[entityName=Mankrik id=73 zone=DECK zonePos=0 cardId=BAR_721 player=1] tag=ZONE value=DECK
""",
        encoding="utf-8",
    )
    assert [card.card_id for card in latest_start_of_game_duplicates(power)] == [
        "BT_123",
        "BAR_721",
    ]
    assert [card.name for card in latest_start_of_game_duplicates(power)] == [
        "Kargath Bladefist",
        "Mankrik",
    ]
