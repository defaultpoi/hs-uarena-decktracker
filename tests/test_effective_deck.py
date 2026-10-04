from hs_uarena_decktracker.effects import latest_deck_effects
from hs_uarena_decktracker.models import ArenaRun, Card, DeckSnapshot, GeneratedDeckCard


def test_generated_card_must_enter_deck(tmp_path):
    power = tmp_path / "Power.log"
    power.write_text(
        """D 01:00:00.0000000 GameState.DebugPrintEntityChoices() - id=2 Player=Local#1 TaskList=1
D 01:00:00.0000000 PowerTaskList.DebugPrintPower() - SHOW_ENTITY - Updating Entity=[entityName=Mankrik id=73 zone=PLAY zonePos=0 cardId=BAR_721 player=2] CardID=BAR_721
D 01:00:00.0000000 PowerTaskList.DebugPrintPower() - FULL_ENTITY - Updating [entityName=Olgra, Mankrik's Wife id=206 zone=SETASIDE zonePos=0 cardId= player=2] CardID=BAR_721t
D 01:00:00.0000000 PowerTaskList.DebugPrintPower() -         tag=CREATOR value=73
D 01:00:01.0000000 PowerTaskList.DebugPrintPower() -     TAG_CHANGE Entity=[entityName=Olgra, Mankrik's Wife id=206 zone=SETASIDE zonePos=0 cardId=BAR_721t player=2] tag=ZONE value=DECK
""",
        encoding="utf-8",
    )
    effects = latest_deck_effects(power)
    assert len(effects) == 1
    effect = effects[0]
    assert effect.card.card_id == "BAR_721t"
    assert effect.source_card.card_id == "BAR_721"
    assert effect.trigger == "CARD_EFFECT"
    assert effect.event == "ADDED_TO_DECK"
    assert effect.entity_id == 206
    assert effect.source_entity_id == 73
    assert effect.in_deck is True
    assert effect.final_zone == "DECK"


def test_opponent_generated_card_is_ignored_when_local_controller_is_known(tmp_path):
    power = tmp_path / "Power.log"
    power.write_text(
        """D 01:00:00.0000000 GameState.DebugPrintEntityChoices() - id=2 Player=Local#1 TaskList=1
D 01:00:00.0000000 GameState.DebugPrintPower() -     Player EntityID=2 PlayerID=1
D 01:00:00.0000000 GameState.DebugPrintPower() -     Player EntityID=3 PlayerID=2
D 01:00:00.0000000 PowerTaskList.DebugPrintPower() - SHOW_ENTITY - Updating Entity=[entityName=Mankrik id=73 zone=PLAY zonePos=0 cardId=BAR_721 player=1] CardID=BAR_721
D 01:00:00.0000000 PowerTaskList.DebugPrintPower() - SHOW_ENTITY - Updating Entity=[entityName=Olgra id=206 zone=SETASIDE zonePos=0 cardId= player=2] CardID=BAR_721t
D 01:00:00.0000000 PowerTaskList.DebugPrintPower() -         tag=CREATOR value=73
D 01:00:01.0000000 PowerTaskList.DebugPrintPower() -     TAG_CHANGE Entity=[entityName=Olgra id=206 zone=SETASIDE zonePos=0 cardId=BAR_721t player=2] tag=ZONE value=DECK
""",
        encoding="utf-8",
    )
    assert latest_deck_effects(power) == []


def test_effective_deck_combines_snapshot_and_generated_cards():
    run = ArenaRun(
        deck_snapshots=[
            DeckSnapshot(
                timestamp="01:00:00",
                deck_id="1",
                cards=(Card("A"), Card("A"), Card("B")),
            )
        ]
    )
    run.deck_effects = [
        GeneratedDeckCard(Card("C"), Card("S"), "CARD_EFFECT", "ADDED_TO_DECK", "test"),
        GeneratedDeckCard(Card("D"), Card("S"), "CARD_EFFECT", "ADDED_TO_DECK", "test"),
    ]
    assert [card.card_id for card in run.effective_deck] == ["A", "A", "B", "C", "D"]
    assert run.effective_deck_counts["A"] == 2



def test_generated_card_never_in_deck_is_not_reported(tmp_path):
    power = tmp_path / "Power.log"
    power.write_text(
        """D 01:00:00.0000000 GameState.DebugPrintEntityChoices() - id=2 Player=Local#1 TaskList=1
D 01:00:00.0000000 PowerTaskList.DebugPrintPower() - SHOW_ENTITY - Updating Entity=[entityName=Mankrik id=73 zone=PLAY zonePos=0 cardId=BAR_721 player=2] CardID=BAR_721
D 01:00:00.0000000 PowerTaskList.DebugPrintPower() - FULL_ENTITY - Updating [entityName=Olgra, Mankrik's Wife id=206 zone=SETASIDE zonePos=0 cardId= player=2] CardID=BAR_721t
D 01:00:00.0000000 PowerTaskList.DebugPrintPower() -         tag=CREATOR value=73
""",
        encoding="utf-8",
    )
    assert latest_deck_effects(power) == []


def test_generated_card_leaving_deck_stays_reported_but_not_in_deck(tmp_path):
    power = tmp_path / "Power.log"
    power.write_text(
        """D 01:00:00.0000000 GameState.DebugPrintEntityChoices() - id=2 Player=Local#1 TaskList=1
D 01:00:00.0000000 PowerTaskList.DebugPrintPower() - SHOW_ENTITY - Updating Entity=[entityName=Mankrik id=73 zone=PLAY zonePos=0 cardId=BAR_721 player=2] CardID=BAR_721
D 01:00:00.0000000 PowerTaskList.DebugPrintPower() - FULL_ENTITY - Updating [entityName=Olgra, Mankrik's Wife id=206 zone=SETASIDE zonePos=0 cardId= player=2] CardID=BAR_721t
D 01:00:00.0000000 PowerTaskList.DebugPrintPower() -         tag=CREATOR value=73
D 01:00:01.0000000 PowerTaskList.DebugPrintPower() -     TAG_CHANGE Entity=[entityName=Olgra, Mankrik's Wife id=206 zone=SETASIDE zonePos=0 cardId=BAR_721t player=2] tag=ZONE value=DECK
D 01:00:02.0000000 PowerTaskList.DebugPrintPower() -     TAG_CHANGE Entity=[entityName=Olgra, Mankrik's Wife id=206 zone=DECK zonePos=0 cardId=BAR_721t player=2] tag=ZONE value=HAND
""",
        encoding="utf-8",
    )
    effects = latest_deck_effects(power)
    assert len(effects) == 1
    assert effects[0].in_deck is False
    assert effects[0].final_zone == "HAND"


def test_block_start_source_is_used_when_never_shown_as_entity(tmp_path):
    power = tmp_path / "Power.log"
    power.write_text(
        """D 01:00:00.0000000 GameState.DebugPrintEntityChoices() - id=2 Player=Local#1 TaskList=1
D 01:00:00.0000000 PowerTaskList.DebugPrintPower() - SHOW_ENTITY - Updating Entity=[entityName=Mankrik id=73 zone=PLAY zonePos=0 cardId=BAR_721 player=2] CardID=BAR_721
D 01:00:00.0000000 PowerTaskList.DebugPrintPower() - BLOCK_START BlockType=POWER Entity=[entityName=Spell Source id=14 zone=HAND zonePos=1 cardId=SRC_001 player=2] EffectCardId=x EffectIndex=0 Target=0 SubOption=-1
D 01:00:00.0000000 PowerTaskList.DebugPrintPower() - SHOW_ENTITY - Updating Entity=[entityName=UNKNOWN ENTITY [cardType=INVALID] id=72 zone=DECK zonePos=0 cardId= player=2] CardID=BT_123
D 01:00:00.0000000 PowerTaskList.DebugPrintPower() -         tag=CREATOR value=14
""",
        encoding="utf-8",
    )
    effects = latest_deck_effects(power)
    assert [(e.source.card_id, e.card.card_id, e.trigger) for e in effects] == [
        ("SRC_001", "BT_123", "CARD_EFFECT")
    ]


def test_only_latest_game_contributes_generated_cards(tmp_path):
    power = tmp_path / "Power.log"
    power.write_text(
        """D 01:00:00.0000000 GameState.DebugPrintPower() - CREATE_GAME
D 01:00:00.0000000 GameState.DebugPrintEntityChoices() - id=2 Player=Local#1 TaskList=1
D 01:00:00.0000000 PowerTaskList.DebugPrintPower() - SHOW_ENTITY - Updating Entity=[entityName=Old Source id=10 zone=DECK zonePos=0 cardId=OLD_001 player=2] CardID=OLD_001
D 01:00:00.0000000 PowerTaskList.DebugPrintPower() - SHOW_ENTITY - Updating Entity=[entityName=Old Generated id=11 zone=DECK zonePos=0 cardId= player=2] CardID=OLD_002
D 01:00:00.0000000 PowerTaskList.DebugPrintPower() -         tag=CREATOR value=10
D 02:00:00.0000000 GameState.DebugPrintPower() - CREATE_GAME
D 02:00:00.0000000 PowerTaskList.DebugPrintPower() - SHOW_ENTITY - Updating Entity=[entityName=New Source id=20 zone=DECK zonePos=0 cardId=NEW_001 player=2] CardID=NEW_001
D 02:00:00.0000000 PowerTaskList.DebugPrintPower() - SHOW_ENTITY - Updating Entity=[entityName=New Generated id=21 zone=DECK zonePos=0 cardId= player=2] CardID=NEW_002
D 02:00:00.0000000 PowerTaskList.DebugPrintPower() -         tag=CREATOR value=20
""",
        encoding="utf-8",
    )
    effects = latest_deck_effects(power)
    assert [effect.card.card_id for effect in effects] == ["NEW_002"]
