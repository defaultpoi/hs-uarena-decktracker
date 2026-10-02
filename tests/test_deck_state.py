from hs_uarena_decktracker.deck_state import latest_deck_removals
from hs_uarena_decktracker.models import Card


def _write_power(tmp_path, body):
    power = tmp_path / "Power.log"
    power.write_text(body, encoding="utf-8")
    return power


def test_drawn_card_is_removed_from_current_deck(tmp_path):
    power = _write_power(
        tmp_path,
        """D 01:00:00.0000000 GameState.DebugPrintEntityChoices() - id=2 Player=Local#1 TaskList=1
D 01:00:00.0000000 PowerTaskList.DebugPrintPower() - SHOW_ENTITY - Updating Entity=[entityName=Card A id=100 zone=DECK zonePos=3 cardId=TEST_A player=2] CardID=TEST_A
D 01:00:01.0000000 PowerTaskList.DebugPrintPower() - TAG_CHANGE Entity=[entityName=Card A id=100 zone=DECK zonePos=3 cardId=TEST_A player=2] tag=ZONE value=HAND
""",
    )
    removals = latest_deck_removals(power, (Card("TEST_A"), Card("TEST_B")))
    assert [card.card_id for card in removals] == ["TEST_A"]


def test_played_card_is_removed_from_current_deck(tmp_path):
    power = _write_power(
        tmp_path,
        """D 01:00:00.0000000 GameState.DebugPrintEntityChoices() - id=2 Player=Local#1 TaskList=1
D 01:00:00.0000000 PowerTaskList.DebugPrintPower() - SHOW_ENTITY - Updating Entity=[entityName=Card A id=100 zone=DECK zonePos=3 cardId=TEST_A player=2] CardID=TEST_A
D 01:00:01.0000000 PowerTaskList.DebugPrintPower() - TAG_CHANGE Entity=[entityName=Card A id=100 zone=DECK zonePos=3 cardId=TEST_A player=2] tag=ZONE value=PLAY
""",
    )
    assert [c.card_id for c in latest_deck_removals(power, (Card("TEST_A"),))] == ["TEST_A"]


def test_shuffled_card_is_not_removed(tmp_path):
    power = _write_power(
        tmp_path,
        """D 01:00:00.0000000 GameState.DebugPrintEntityChoices() - id=2 Player=Local#1 TaskList=1
D 01:00:00.0000000 PowerTaskList.DebugPrintPower() - SHOW_ENTITY - Updating Entity=[entityName=Card A id=100 zone=DECK zonePos=3 cardId=TEST_A player=2] CardID=TEST_A
D 01:00:01.0000000 PowerTaskList.DebugPrintPower() - TAG_CHANGE Entity=[entityName=Card A id=100 zone=HAND zonePos=3 cardId=TEST_A player=2] tag=ZONE value=DECK
""",
    )
    assert latest_deck_removals(power, (Card("TEST_A"),)) == []


def test_generated_card_leaving_deck_does_not_remove_same_named_draft_card(tmp_path):
    power = _write_power(
        tmp_path,
        """D 01:00:00.0000000 GameState.DebugPrintEntityChoices() - id=2 Player=Local#1 TaskList=1
D 01:00:00.0000000 PowerTaskList.DebugPrintPower() - SHOW_ENTITY - Updating Entity=[entityName=Source id=50 zone=PLAY zonePos=0 cardId=SOURCE player=2] CardID=SOURCE
D 01:00:00.0000000 PowerTaskList.DebugPrintPower() - SHOW_ENTITY - Updating Entity=[entityName=Card A id=100 zone=DECK zonePos=3 cardId=TEST_A player=2] CardID=TEST_A
D 01:00:00.0000000 PowerTaskList.DebugPrintPower() - SHOW_ENTITY - Updating Entity=[entityName=Card A id=101 zone=SETASIDE zonePos=0 cardId= player=2] CardID=TEST_A
D 01:00:00.0000000 PowerTaskList.DebugPrintPower() -         tag=CREATOR value=50
D 01:00:01.0000000 PowerTaskList.DebugPrintPower() - TAG_CHANGE Entity=[entityName=Card A id=101 zone=SETASIDE zonePos=0 cardId=TEST_A player=2] tag=ZONE value=HAND
""",
    )
    removals = latest_deck_removals(power, (Card("TEST_A"),))
    assert removals == []


def test_only_latest_game_contributes_removals(tmp_path):
    power = _write_power(
        tmp_path,
        """D 01:00:00.0000000 GameState.DebugPrintPower() - CREATE_GAME
D 01:00:00.0000000 GameState.DebugPrintEntityChoices() - id=2 Player=Local#1 TaskList=1
D 01:00:00.0000000 PowerTaskList.DebugPrintPower() - SHOW_ENTITY - Updating Entity=[entityName=Old id=10 zone=DECK zonePos=1 cardId=TEST_A player=2] CardID=TEST_A
D 01:00:01.0000000 PowerTaskList.DebugPrintPower() - TAG_CHANGE Entity=[entityName=Old id=10 zone=DECK zonePos=1 cardId=TEST_A player=2] tag=ZONE value=HAND
D 02:00:00.0000000 GameState.DebugPrintPower() - CREATE_GAME
D 02:00:00.0000000 GameState.DebugPrintEntityChoices() - id=20 Player=Local#1 TaskList=1
D 02:00:00.0000000 PowerTaskList.DebugPrintPower() - SHOW_ENTITY - Updating Entity=[entityName=Current id=20 zone=DECK zonePos=1 cardId=TEST_A player=2] CardID=TEST_A
""",
    )
    assert latest_deck_removals(power, (Card("TEST_A"),)) == []
