from hs_uarena_decktracker.effects import latest_deck_effects
from hs_uarena_decktracker.models import ArenaRun, Card, DeckSnapshot


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
        type("Effect", (), {"card": Card("C")})(),
        type("Effect", (), {"card": Card("D")})(),
    ]
    assert [card.card_id for card in run.effective_deck] == ["A", "A", "B", "C", "D"]
    assert run.effective_deck_counts["A"] == 2
