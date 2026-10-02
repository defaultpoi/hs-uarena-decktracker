from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from .card_db import CardDatabase
from .models import Card

_PLAYER_CHOICE = re.compile(
    r"GameState\.DebugPrintEntityChoices\(\) - id=(?P<entity_id>\d+) "
    r"Player=(?P<player>.+?) TaskList="
)
_SHOW_ENTITY = re.compile(
    r"SHOW_ENTITY - Updating Entity=\[entityName=(?P<name>.*?) "
    r"id=(?P<entity_id>\d+) zone=(?P<zone>\S+) zonePos=.*? "
    r"cardId=(?P<card_id>\S*) player=(?P<player>\d+)\] "
    r"CardID=(?P<shown_card_id>\S+)"
)
_TAG = re.compile(r"tag=(?P<tag>\S+) value=(?P<value>.+?)\s*$")
_START_OF_GAME = re.compile(
    r"BLOCK_START .*?Entity=\[entityName=(?P<name>.*?) "
    r"id=(?P<entity_id>\d+) .*?cardId=(?P<card_id>\S+) "
    r"player=(?P<player>\d+)\].*?TriggerKeyword=START_OF_GAME_KEYWORD"
)

@dataclass(frozen=True)
class DeckEffect:
    source: Card
    generated: Card
    trigger: str
    reason: str

@dataclass
class _Entity:
    card_id: str
    name: str | None
    player: int
    zone: str

def _card(card_id: str, name: str | None, database: CardDatabase | None) -> Card:
    data = database.get(card_id) if database is not None else None
    log_name = name if name and not name.startswith("UNKNOWN ENTITY") else None\n    return Card(card_id, log_name or (data.name if data else None), data.text if data else None)

def latest_deck_effects(path: str | Path, database: CardDatabase | None = None) -> list[DeckEffect]:
    """Return generated cards placed into the local player's deck."""
    path = Path(path)
    if not path.is_file():
        return []

    lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    local_player_ids = {
        int(match.group("entity_id"))
        for line in lines
        if (match := _PLAYER_CHOICE.search(line))
        and match.group("player").strip() not in {"UNKNOWN HUMAN PLAYER", "UNKNOWN PLAYER"}
    }
    if not local_player_ids:
        return []

    entities: dict[int, _Entity] = {}
    generated: list[tuple[int, int]] = []
    start_creators: set[int] = set()
    pending_id: int | None = None

    for line in lines:
        start = _START_OF_GAME.search(line)
        if start and int(start.group("player")) in local_player_ids:
            start_creators.add(int(start.group("entity_id")))
            entities.setdefault(
                int(start.group("entity_id")),
                _Entity(start.group("card_id"), start.group("name"), int(start.group("player")), "DECK"),
            )

        show = _SHOW_ENTITY.search(line)
        if show:
            entity_id = int(show.group("entity_id"))
            if int(show.group("player")) in local_player_ids:
                entities[entity_id] = _Entity(
                    show.group("shown_card_id"),
                    show.group("name") or None,
                    int(show.group("player")),
                    show.group("zone"),
                )
                pending_id = entity_id
            else:
                pending_id = None
            continue

        if pending_id is None:
            continue

        tag = _TAG.search(line)
        if not tag:
            continue
        if tag.group("tag") == "CREATOR":
            try:
                generated.append((pending_id, int(tag.group("value"))))
            except ValueError:
                pass
        elif tag.group("tag") == "ZONE":
            entities[pending_id].zone = tag.group("value")

    effects: list[DeckEffect] = []
    seen: set[tuple[int, int]] = set()
    for entity_id, creator_id in generated:
        entity = entities.get(entity_id)
        source = entities.get(creator_id)
        if entity is None or source is None or entity.zone != "DECK":
            continue
        key = (entity_id, creator_id)
        if key in seen:
            continue
        seen.add(key)
        trigger = "START_OF_GAME" if creator_id in start_creators else "CARD_EFFECT"
        reason = (
            "Start of Game effect copied this card into the deck"
            if trigger == "START_OF_GAME"
            else "Card effect created this card in the deck"
        )
        effects.append(
            DeckEffect(
                source=_card(source.card_id, source.name, database),
                generated=_card(entity.card_id, entity.name, database),
                trigger=trigger,
                reason=reason,
            )
        )
    return effects
