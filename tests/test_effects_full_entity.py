from hs_uarena_decktracker.card_db import CardDatabase
from hs_uarena_decktracker.effects import latest_deck_effects


def test_parses_start_of_game_and_card_effect_generated_cards(tmp_path):
    power = tmp_path / "Power.log"
    power.write_text(
        """D 01:00:00.0000000 GameState.DebugPrintEntityChoices() - id=2 Player=Local#1 TaskList=1
D 01:00:00.0000000 PowerTaskList.DebugPrintPower() - SHOW_ENTITY - Updating Entity=[entityName=Mankrik id=73 zone=PLAY zonePos=0 cardId=BAR_721 player=2] CardID=BAR_721
D 01:00:00.0000000 PowerTaskList.DebugPrintPower() - BLOCK_START BlockType=TRIGGER Entity=[entityName=Chainbreaker Hogger id=14 zone=DECK zonePos=0 cardId=JAIL_384 player=2] EffectCardId=x EffectIndex=1 Target=0 SubOption=-1 TriggerKeyword=START_OF_GAME_KEYWORD
D 01:00:00.0000000 PowerTaskList.DebugPrintPower() - SHOW_ENTITY - Updating Entity=[entityName=UNKNOWN ENTITY [cardType=INVALID] id=72 zone=DECK zonePos=0 cardId= player=2] CardID=BT_123
D 01:00:00.0000000 PowerTaskList.DebugPrintPower() -         tag=CREATOR value=14
D 01:00:00.0000000 PowerTaskList.DebugPrintPower() -     BLOCK_END
D 01:00:00.0000000 PowerTaskList.DebugPrintPower() - SHOW_ENTITY - Updating Entity=[entityName=UNKNOWN ENTITY [cardType=INVALID] id=74 zone=DECK zonePos=0 cardId= player=2] CardID=BAR_721t
D 01:00:00.0000000 PowerTaskList.DebugPrintPower() -         tag=CREATOR value=73
D 01:00:00.0000000 PowerTaskList.DebugPrintPower() - SHOW_ENTITY - Updating Entity=[entityName=Opponent copy id=91 zone=DECK zonePos=0 cardId= player=1] CardID=BT_123
D 01:00:00.0000000 PowerTaskList.DebugPrintPower() -         tag=CREATOR value=73
""",
        encoding="utf-8",
    )

    effects = latest_deck_effects(power)
    assert [(e.source.card_id, e.generated.card_id, e.trigger) for e in effects] == [
        ("JAIL_384", "BT_123", "START_OF_GAME"),
        ("BAR_721", "BAR_721t", "CARD_EFFECT"),
    ]


def test_effect_parser_enriches_cards_from_database(tmp_path):
    cache = tmp_path / "cards.json"
    cache.write_text(
        '{"cards":[{"id":"BAR_721","name":"Mankrik","text":"Battlecry: Put Olgra into your deck."},{"id":"BAR_721t","name":"Olgra, Mankrik\'s Wife","text":"Casts When Drawn."}]}',
        encoding="utf-8",
    )
    database = CardDatabase(cache)
    database.load()

    power = tmp_path / "Power.log"
    power.write_text(
        """D 01:00:00.0000000 GameState.DebugPrintEntityChoices() - id=2 Player=Local#1 TaskList=1
D 01:00:00.0000000 PowerTaskList.DebugPrintPower() - SHOW_ENTITY - Updating Entity=[entityName=Mankrik id=73 zone=PLAY zonePos=0 cardId=BAR_721 player=2] CardID=BAR_721
D 01:00:00.0000000 PowerTaskList.DebugPrintPower() - SHOW_ENTITY - Updating Entity=[entityName=UNKNOWN ENTITY [cardType=INVALID] id=74 zone=DECK zonePos=0 cardId= player=2] CardID=BAR_721t
D 01:00:00.0000000 PowerTaskList.DebugPrintPower() -         tag=CREATOR value=73
""",
        encoding="utf-8",
    )

    effects = latest_deck_effects(power, database)
    assert effects[0].source.name == "Mankrik"
    assert effects[0].source.text == "Battlecry: Put Olgra into your deck."
    assert effects[0].generated.name == "Olgra, Mankrik's Wife"
    assert effects[0].generated.text == "Casts When Drawn."


def test_drafted_card_without_creator_is_not_a_generated_effect(tmp_path):
    power = tmp_path / "Power.log"
    power.write_text(
        """D 01:00:00.0000000 GameState.DebugPrintEntityChoices() - id=2 Player=Local#1 TaskList=1
D 01:00:00.0000000 PowerTaskList.DebugPrintPower() - SHOW_ENTITY - Updating Entity=[entityName=Drafted Card id=75 zone=DECK zonePos=1 cardId=BT_123 player=2] CardID=BT_123
""",
        encoding="utf-8",
    )
    assert latest_deck_effects(power) == []


def test_parses_full_entity_generation_and_later_deck_zone(tmp_path):
    power = tmp_path / "Power.log"
    power.write_text(
        """\
D 06:31:01.0000000 GameState.DebugPrintEntityChoices() - id=2 Player=Local#1 TaskList=1
D 06:31:01.0000000 PowerTaskList.DebugPrintPower() - SHOW_ENTITY - Updating Entity=[entityName=Mankrik id=73 zone=PLAY zonePos=3 cardId=BAR_721 player=2] CardID=BAR_721
D 06:31:01.0000000 PowerTaskList.DebugPrintPower() - BLOCK_START BlockType=POWER Entity=[entityName=Mankrik id=73 zone=PLAY zonePos=3 cardId=BAR_721 player=2]
D 06:31:01.0000000 PowerTaskList.DebugPrintPower() -     FULL_ENTITY - Updating [entityName=Olgra, Mankrik's Wife id=206 zone=SETASIDE zonePos=0 cardId=BAR_721t player=2] CardID=BAR_721t
D 06:31:01.0000000 PowerTaskList.DebugPrintPower() -         tag=CREATOR value=73
D 06:31:01.0000000 PowerTaskList.DebugPrintPower() -         tag=CASTS_WHEN_DRAWN value=1
D 06:31:01.0000000 PowerTaskList.DebugPrintPower() -     TAG_CHANGE Entity=[entityName=Olgra, Mankrik's Wife id=206 zone=SETASIDE zonePos=0 cardId=BAR_721t player=2] tag=ZONE value=DECK
D 06:31:01.0000000 PowerTaskList.DebugPrintPower() - BLOCK_END
""",
        encoding="utf-8",
    )

    effects = latest_deck_effects(power)
    assert [(e.source.card_id, e.generated.card_id, e.trigger) for e in effects] == [
        ("BAR_721", "BAR_721t", "CARD_EFFECT")
    ]
