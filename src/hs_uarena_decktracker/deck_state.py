from __future__ import annotations

import re
from collections import Counter
from pathlib import Path

from .models import Card


_PLAYER_CHOICE = re.compile(
    r"GameState\.DebugPrintEntityChoices\(\) - id=(?P<entity_id>\d+) "
    r"Player=(?P<player>.+?) TaskList="
)
_CREATE_GAME = re.compile(r"GameState\.DebugPrintPower\(\) - CREATE_GAME\s*$")
_ENTITY = re.compile(
    r"(?:SHOW_ENTITY|FULL_ENTITY) - (?:Creating ID=\d+ CardID=\S+|Updating )"
    r"(?:Entity=)?\[entityName=.*? id=(?P<entity_id>\d+) "
    r"zone=(?P<zone>\S+) zonePos=.*? cardId=(?P<card_id>\S*) "
    r"player=(?P<player>\d+)\](?: CardID=(?P<shown_card_id>\S+))?"
)
_TAG_CHANGE = re.compile(
    r"TAG_CHANGE Entity=\[entityName=.*? id=(?P<entity_id>\d+) .*?\] "
    r"tag=(?P<tag>\S+) value=(?P<value>.+?)\s*$"
)
_TAG = re.compile(r"tag=(?P<tag>\S+) value=(?P<value>.+?)\s*$")


class _Entity:
    __slots__ = ("card_id", "player", "zone", "creator_id", "ever_in_deck")

    def __init__(
        self,
        card_id: str,
        player: int,
        zone: str,
        creator_id: int | None = None,
        ever_in_deck: bool = False,
    ) -> None:
        self.card_id = card_id
        self.player = player
        self.zone = zone
        self.creator_id = creator_id
        self.ever_in_deck = ever_in_deck


def _latest_game_lines(path: Path) -> list[str]:
    lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    starts = [i for i, line in enumerate(lines) if _CREATE_GAME.search(line)]
    return lines[starts[-1] :] if starts else lines


def _local_player_id(lines: list[str]) -> int | None:
    for index, line in enumerate(lines[:1200]):
        choice = _PLAYER_CHOICE.search(line)
        if not choice:
            continue
        if choice.group("player").strip() in {"UNKNOWN HUMAN PLAYER", "UNKNOWN PLAYER"}:
            continue
        for following in lines[index + 1 : index + 12]:
            match = re.search(r"player=(?P<player>\d+)\]", following)
            if match:
                return int(match.group("player"))
        # Small fixtures may only expose the choice entity id.
        return int(choice.group("entity_id"))
    return None


def latest_deck_removals(
    path: str | Path,
    deck_cards: tuple[Card, ...],
) -> list[Card]:
    """Return draft-deck cards that have left DECK in the latest game.

    A card is considered removed only after it was observed in DECK and its
    final observed zone is not DECK. Generated entities are excluded because
    they are tracked separately by the generated-card effect layer.
    """
    path = Path(path)
    if not path.is_file() or not deck_cards:
        return []

    lines = _latest_game_lines(path)
    local_player = _local_player_id(lines)
    if local_player is None:
        return []

    entities: dict[int, _Entity] = {}
    generated: set[int] = set()
    current_entity: int | None = None

    for line in lines:
        entity = _ENTITY.search(line)
        if entity:
            entity_id = int(entity.group("entity_id"))
            player = int(entity.group("player"))
            if player != local_player:
                current_entity = None
                continue

            previous = entities.get(entity_id)
            zone = entity.group("zone")
            card_id = entity.group("shown_card_id") or entity.group("card_id")
            state = _Entity(
                card_id=card_id,
                player=player,
                zone=zone,
                creator_id=previous.creator_id if previous else None,
                ever_in_deck=(previous.ever_in_deck if previous else False) or zone == "DECK",
            )
            entities[entity_id] = state
            current_entity = entity_id
            continue

        tag_change = _TAG_CHANGE.search(line)
        if tag_change:
            state = entities.get(int(tag_change.group("entity_id")))
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
                        generated.add(int(tag_change.group("entity_id")))
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
                    generated.add(current_entity)

        if "BLOCK_END" in line:
            current_entity = None

    deck_counts = Counter(card.card_id for card in deck_cards)
    left_counts: Counter[str] = Counter()

    for entity_id, state in entities.items():
        if (
            entity_id not in generated
            and state.ever_in_deck
            and state.zone != "DECK"
            and state.card_id in deck_counts
        ):
            left_counts[state.card_id] += 1

    removals: list[Card] = []
    for card in deck_cards:
        if left_counts[card.card_id] <= 0:
            continue
        removals.append(card)
        left_counts[card.card_id] -= 1

    return removals
