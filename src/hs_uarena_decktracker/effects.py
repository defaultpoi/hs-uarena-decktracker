from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from .card_db import CardDatabase
from .models import Card, GeneratedDeckCard


_PLAYER_CHOICE = re.compile(
    r"GameState\.DebugPrintEntityChoices\(\) - id=(?P<entity_id>\d+) "
    r"Player=(?P<player>.+?) TaskList="
)
_CREATE_GAME = re.compile(r"GameState\.DebugPrintPower\(\) - CREATE_GAME\s*$")
_ENTITY = re.compile(
    r"(?P<kind>SHOW_ENTITY|FULL_ENTITY) - (?:Updating )?"
    r"(?:Entity=)?\[entityName=(?P<name>.*?) id=(?P<entity_id>\d+) "
    r"zone=(?P<zone>\S+) zonePos=.*? cardId=(?P<card_id>\S*) "
    r"player=(?P<player>\d+)\](?: CardID=(?P<shown_card_id>\S+))?"
)
_SIMPLE_ENTITY = re.compile(
    r"(?:SHOW_ENTITY|FULL_ENTITY) - Updating Entity=\[entityName=(?P<name>.*?) "
    r"id=(?P<entity_id>\d+) zone=(?P<zone>\S+) zonePos=.*? "
    r"cardId=(?P<card_id>\S*) player=(?P<player>\d+)\] CardID=(?P<shown>\S+)"
)
_TAG = re.compile(r"tag=(?P<tag>\S+) value=(?P<value>.+?)\s*$")
_ZONE_ENTITY = re.compile(
    r"TAG_CHANGE Entity=\[entityName=(?P<name>.*?) id=(?P<entity_id>\d+) "
    r"zone=(?P<zone>\S+) zonePos=.*? cardId=(?P<card_id>\S*) "
    r"player=(?P<player>\d+)\] tag=ZONE value=(?P<new_zone>\S+)"
)
_BLOCK_START = re.compile(
    r"BLOCK_START .*?Entity=\[entityName=(?P<name>.*?) id=(?P<entity_id>\d+) "
    r".*?cardId=(?P<card_id>\S+) player=(?P<player>\d+)\].*?"
    r"TriggerKeyword=(?P<trigger>\S+)"
)


@dataclass
class _Entity:
    card_id: str
    name: str | None
    player: int
    zone: str
    creator_id: int | None = None
    first_zone: str | None = None


def _card(card_id: str, name: str | None, database: CardDatabase | None) -> Card:
    data = database.get(card_id) if database is not None else None
    log_name = name if name and not name.startswith("UNKNOWN ENTITY") else None
    return Card(
        card_id,
        log_name or (data.name if data else None),
        data.text if data else None,
    )


def latest_deck_effects(
    path: str | Path,
    database: CardDatabase | None = None,
) -> list[GeneratedDeckCard]:
    """Return generated cards currently observed in the local player's deck.

    The parser scopes itself to the latest CREATE_GAME in Power.log. This avoids
    carrying generated cards from an earlier game into the current deck state.
    An entity may be created in SETASIDE/FULL_ENTITY first and enter DECK later;
    the event is emitted only when its latest zone is DECK.
    """
    path = Path(path)
    if not path.is_file():
        return []

    lines = path.read_text(encoding="utf-8", errors="replace").splitlines()

    local_entity_ids: set[int] = set()
    local_player_ids: set[int] = set()
    for line in lines:
        match = _PLAYER_CHOICE.search(line)
        if not match:
            continue
        player = match.group("player").strip()
        if player not in {"UNKNOWN HUMAN PLAYER", "UNKNOWN PLAYER"}:
            local_entity_ids.add(int(match.group("entity_id")))

    # In normal logs the player entity id is 2/3 while card controller is 1/2.
    # Entity choices expose the player's controller through later entity records,
    # so collect the controller id from the latest game instead of hard-coding it.
    latest_game_start = max(
        (i for i, line in enumerate(lines) if _CREATE_GAME.search(line)),
        default=0,
    )
    lines = lines[latest_game_start:]

    entities: dict[int, _Entity] = {}
    generated_candidates: set[int] = set()
    start_sources: set[int] = set()
    active_source: int | None = None
    current_game_index = sum(1 for line in lines[:latest_game_start] if _CREATE_GAME.search(line))

    # First pass identifies the local controller from known player entities.
    for line in lines[:1200]:
        match = re.search(
            r"Player EntityID=(?P<entity_id>\d+) PlayerID=(?P<player_id>\d+)",
            line,
        )
        if match:
            entity_id = int(match.group("entity_id"))
            player_id = int(match.group("player_id"))
            if entity_id in local_entity_ids:
                local_player_ids.add(player_id)

    for line in lines:
        block = _BLOCK_START.search(line)
        if block and block.group("trigger") == "START_OF_GAME_KEYWORD":
            player = int(block.group("player"))
            if player in local_player_ids or not local_player_ids:
                start_sources.add(int(block.group("entity_id")))
                active_source = int(block.group("entity_id"))
            else:
                active_source = None

        entity_match = _SIMPLE_ENTITY.search(line)
        if entity_match:
            entity_id = int(entity_match.group("entity_id"))
            player = int(entity_match.group("player"))
            card_id = entity_match.group("shown") or entity_match.group("card_id")
            if player in local_player_ids or not local_player_ids:
                entities[entity_id] = _Entity(
                    card_id=card_id,
                    name=entity_match.group("name"),
                    player=player,
                    zone=entity_match.group("zone"),
                    first_zone=entity_match.group("zone"),
                )
            else:
                entities.pop(entity_id, None)
            continue

        zone_match = _ZONE_ENTITY.search(line)
        if zone_match:
            entity_id = int(zone_match.group("entity_id"))
            entity = entities.get(entity_id)
            if entity is not None:
                entity.zone = zone_match.group("new_zone")
            continue

        tag = _TAG.search(line)
        if tag and entities:
            # Tags following an entity update belong to the most recently updated
            # entity. Keep this deliberately local to the current log block.
            pass

        if "BLOCK_END" in line:
            active_source = None

    # The previous pass needs creator tags associated with each entity. Re-run the
    # latest game with a small state machine because Hearthstone emits tags on
    # separate lines from FULL_ENTITY/SHOW_ENTITY.
    entities.clear()
    current_entity: int | None = None
    active_source = None
    start_sources.clear()

    for line in lines:
        block = _BLOCK_START.search(line)
        if block:
            trigger = block.group("trigger")
            source_id = int(block.group("entity_id"))
            if trigger == "START_OF_GAME_KEYWORD":
                start_sources.add(source_id)
            active_source = source_id

        entity_match = _SIMPLE_ENTITY.search(line)
        if entity_match:
            entity_id = int(entity_match.group("entity_id"))
            player = int(entity_match.group("player"))
            if local_player_ids and player not in local_player_ids:
                current_entity = None
                continue
            card_id = entity_match.group("shown") or entity_match.group("card_id")
            entities[entity_id] = _Entity(
                card_id=card_id,
                name=entity_match.group("name"),
                player=player,
                zone=entity_match.group("zone"),
                first_zone=entity_match.group("zone"),
            )
            current_entity = entity_id
            continue

        zone_match = _ZONE_ENTITY.search(line)
        if zone_match:
            entity_id = int(zone_match.group("entity_id"))
            entity = entities.get(entity_id)
            if entity is not None:
                entity.zone = zone_match.group("new_zone")
            continue

        tag = _TAG.search(line)
        if tag and current_entity is not None:
            entity = entities.get(current_entity)
            if entity is not None and tag.group("tag") == "CREATOR":
                try:
                    entity.creator_id = int(tag.group("value"))
                    generated_candidates.add(current_entity)
                except ValueError:
                    pass

        if "BLOCK_END" in line:
            active_source = None
            current_entity = None

    effects: list[GeneratedDeckCard] = []
    for entity_id in sorted(generated_candidates):
        entity = entities.get(entity_id)
        if entity is None or entity.zone != "DECK" or entity.creator_id is None:
            continue
        source = entities.get(entity.creator_id)
        if source is None:
            continue
        trigger = "START_OF_GAME" if entity.creator_id in start_sources else "CARD_EFFECT"
        reason = (
            "Start of Game effect added this card to the deck"
            if trigger == "START_OF_GAME"
            else "Card effect added this card to the deck"
        )
        effects.append(
            GeneratedDeckCard(
                card=_card(entity.card_id, entity.name, database),
                source_card=_card(source.card_id, source.name, database),
                trigger=trigger,
                event="ADDED_TO_DECK",
                reason=reason,
                entity_id=entity_id,
                source_entity_id=entity.creator_id,
                game_index=current_game_index,
            )
        )
    return effects
