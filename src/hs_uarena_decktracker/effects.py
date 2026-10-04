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
    r"(?:SHOW_ENTITY|FULL_ENTITY) - (?:Creating ID=\d+ CardID=\S+|Updating )"
    r"(?:Entity=)?\[entityName=(?P<name>.*?) id=(?P<entity_id>\d+) "
    r"zone=(?P<zone>\S+) zonePos=.*? cardId=(?P<card_id>\S*) "
    r"player=(?P<player>\d+)\](?: CardID=(?P<shown_card_id>\S+))?"
)
_BLOCK_START = re.compile(
    r"BLOCK_START .*?Entity=\[entityName=(?P<name>.*?) id=(?P<entity_id>\d+) "
    r".*?cardId=(?P<card_id>\S+) player=(?P<player>\d+)\].*?"
    r"TriggerKeyword=(?P<trigger>\S+)"
)
_BLOCK_SOURCE = re.compile(
    r"BLOCK_START .*?Entity=\[entityName=(?P<name>.*?) id=(?P<entity_id>\d+) "
    r"zone=(?P<zone>\S+) zonePos=.*? cardId=(?P<card_id>\S*) "
    r"player=(?P<player>\d+)\]"
)
_TAG_CHANGE = re.compile(
    r"TAG_CHANGE Entity=\[entityName=.*? id=(?P<entity_id>\d+) .*?\] "
    r"tag=(?P<tag>\S+) value=(?P<value>.+?)\s*$"
)
_TAG = re.compile(r"tag=(?P<tag>\S+) value=(?P<value>.+?)\s*$")


@dataclass
class _Entity:
    card_id: str
    name: str | None
    player: int
    zone: str
    creator_id: int | None = None
    ever_in_deck: bool = False


def _card(card_id: str, name: str | None, database: CardDatabase | None) -> Card:
    data = database.get(card_id) if database is not None and card_id else None
    log_name = name if name and not name.startswith("UNKNOWN ENTITY") else None
    if data is None and log_name and database is not None:
        matches = database.find_by_name(log_name)
        if len(matches) == 1:
            data = matches[0]
            card_id = data.card_id
    return Card(
        card_id,
        log_name or (data.name if data else None),
        data.text if data else None,
    )


def latest_deck_effects(
    path: str | Path,
    database: CardDatabase | None = None,
) -> list[GeneratedDeckCard]:
    """Return generated cards still observed in the local player's deck.

    Only the latest CREATE_GAME is considered. This prevents generated cards
    from a previous game from being carried into the current deck state.

    Hearthstone can create a generated card in SETASIDE and move it into DECK
    later. The event is therefore emitted only when the final observed zone is
    DECK, not merely when the entity is first created.
    """
    path = Path(path)
    if not path.is_file():
        return []

    all_lines = path.read_text(encoding="utf-8", errors="replace").splitlines()

    create_indices = [
        index for index, line in enumerate(all_lines) if _CREATE_GAME.search(line)
    ]
    latest_start = create_indices[-1] if create_indices else 0
    game_index = len(create_indices)
    lines = all_lines[latest_start:]

    # DebugPrintEntityChoices identifies the local player by name and also
    # includes one or more entity records with that player's numeric controller.
    # Use the first non-placeholder choice in the latest game rather than
    # assuming PlayerID=1/2.
    local_player_ids: set[int] = set()
    for index, line in enumerate(lines[:1200]):
        choice = _PLAYER_CHOICE.search(line)
        if not choice or choice.group("player").strip() in {"UNKNOWN HUMAN PLAYER", "UNKNOWN PLAYER"}:
            continue
        for following in lines[index + 1:index + 12]:
            entity = re.search(r"player=(?P<player>\d+)\]", following)
            if entity:
                local_player_ids.add(int(entity.group("player")))
                break
        if local_player_ids:
            break

    # Compact fixtures may omit the choice entity list; their choice id is the
    # only local-player identity available.
    if not local_player_ids:
        for line in lines[:1200]:
            choice = _PLAYER_CHOICE.search(line)
            if choice and choice.group("player").strip() not in {"UNKNOWN HUMAN PLAYER", "UNKNOWN PLAYER"}:
                local_player_ids.add(int(choice.group("entity_id")))
                break

    def is_local(player: int) -> bool:
        # When the local controller cannot be identified, do not filter.
        return not local_player_ids or player in local_player_ids

    entities: dict[int, _Entity] = {}
    generated_order: list[int] = []
    start_sources: set[int] = set()
    current_entity: int | None = None

    for line in lines:
        block = _BLOCK_START.search(line)
        if block and block.group("trigger") == "START_OF_GAME_KEYWORD":
            if is_local(int(block.group("player"))):
                start_sources.add(int(block.group("entity_id")))

        # A block's source entity may only ever be described by the BLOCK_START
        # line itself (e.g. Start of Game sources still in the deck), so record
        # it unless a fuller entity record has already been seen.
        source_block = _BLOCK_SOURCE.search(line)
        if source_block:
            source_id = int(source_block.group("entity_id"))
            source_player = int(source_block.group("player"))
            if source_id not in entities and is_local(source_player):
                entities[source_id] = _Entity(
                    card_id=source_block.group("card_id"),
                    name=source_block.group("name"),
                    player=source_player,
                    zone=source_block.group("zone"),
                )

        entity = _ENTITY.search(line)
        if entity:
            entity_id = int(entity.group("entity_id"))
            player = int(entity.group("player"))
            if not is_local(player):
                current_entity = None
                continue

            card_id = entity.group("shown_card_id") or entity.group("card_id")
            previous = entities.get(entity_id)
            entities[entity_id] = _Entity(
                card_id=card_id,
                name=entity.group("name"),
                player=player,
                zone=entity.group("zone"),
                creator_id=previous.creator_id if previous else None,
                ever_in_deck=(
                    (previous.ever_in_deck if previous else False)
                    or entity.group("zone") == "DECK"
                ),
            )
            current_entity = entity_id
            continue

        tag_change = _TAG_CHANGE.search(line)
        if tag_change:
            entity_id = int(tag_change.group("entity_id"))
            state = entities.get(entity_id)
            if state is not None:
                tag = tag_change.group("tag")
                value = tag_change.group("value").strip()
                if tag == "ZONE":
                    state.zone = value
                    if value == "DECK":
                        state.ever_in_deck = True
                elif tag == "CREATOR":
                    try:
                        state.creator_id = int(value)
                    except ValueError:
                        pass
                    else:
                        if entity_id not in generated_order:
                            generated_order.append(entity_id)
            current_entity = None
            continue

        tag = _TAG.search(line)
        if tag and current_entity is not None:
            state = entities.get(current_entity)
            if state is not None and tag.group("tag") == "CREATOR":
                try:
                    state.creator_id = int(tag.group("value"))
                except ValueError:
                    pass
                else:
                    if current_entity not in generated_order:
                        generated_order.append(current_entity)

        if "BLOCK_END" in line:
            current_entity = None

    effects: list[GeneratedDeckCard] = []
    for entity_id in generated_order:
        entity = entities.get(entity_id)
        if entity is None or entity.creator_id is None or not entity.ever_in_deck:
            continue

        source = entities.get(entity.creator_id)
        if source is None:
            continue

        trigger = (
            "START_OF_GAME"
            if entity.creator_id in start_sources
            else "CARD_EFFECT"
        )
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
                game_index=game_index,
                in_deck=entity.zone == "DECK",
                final_zone=entity.zone,
            )
        )

    return effects
