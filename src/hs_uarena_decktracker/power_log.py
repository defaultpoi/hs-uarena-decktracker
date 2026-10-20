from __future__ import annotations

import re
from pathlib import Path

from .models import Card, DeckEffect


_UNDERGROUND = re.compile(r"GameType=GT_UNDERGROUND_ARENA\b")
_LOCAL_PLAYER = re.compile(
    r"GameState\.DebugPrintEntityChoices\(\) - .*Player=(?P<player>.+?) TaskList="
)
_RESULT = re.compile(
    r"PowerTaskList\.DebugPrintPower\(\) - .*"
    r"Entity=(?P<player>.+?) tag=PLAYSTATE value=(?P<result>LOST|WON)\b"
)
_START_OF_GAME = re.compile(
    r"PowerTaskList\.DebugPrintPower\(\) - BLOCK_START .*"
    r"Entity=\[entityName=(?P<name>.*?) id=(?P<entity_id>\d+) .*"
    r"cardId=(?P<card_id>\S+) player=(?P<player>\d+)\].*"
    r"TriggerKeyword=START_OF_GAME_KEYWORD"
)
_COPIED_ENTITY = re.compile(
    r"SHOW_ENTITY - Updating Entity=\[entityName=.*? id=(?P<entity_id>\d+) .*"
    r"cardId=.*? player=\d+\] CardID=(?P<card_id>\S+)"
)
_TAG_CREATOR = re.compile(r"tag=CREATOR value=(?P<creator>\d+)\s*$")
_TAG_COPIED = re.compile(r"tag=COPIED_FROM_ENTITY_ID value=(?P<source>\d+)\s*$")
_ENTITY = re.compile(
    r"Entity=\[entityName=(?P<name>.*?) id=(?P<entity_id>\d+) .*"
    r"cardId=(?P<card_id>\S+) player=\d+\]"
)


def is_underground_arena(path: str | Path) -> bool:
    """Return True only when Power.log identifies an Underground Arena game."""
    path = Path(path)
    if not path.is_file():
        return False

    with path.open("r", encoding="utf-8", errors="replace") as handle:
        return any(_UNDERGROUND.search(line) for line in handle)


def game_results(path: str | Path) -> list[str]:
    """Return terminal results for the local player in log order."""
    path = Path(path)
    if not path.is_file():
        return []

    local_player: str | None = None
    results: list[str] = []
    with path.open("r", encoding="utf-8", errors="replace") as handle:
        for line in handle:
            if local_player is None:
                choice = _LOCAL_PLAYER.search(line)
                if choice:
                    candidate = choice.group("player").strip()
                    if candidate not in {"UNKNOWN HUMAN PLAYER", "UNKNOWN PLAYER"}:
                        local_player = candidate
            if local_player is not None:
                match = _RESULT.search(line)
                if match and match.group("player") == local_player:
                    results.append(match.group("result"))
    return results


def latest_result(path: str | Path) -> str | None:
    """Return the latest terminal result for the local player, if known."""
    results = game_results(path)
    return results[-1] if results else None


def count_losses(path: str | Path) -> int:
    """Count losses for the local player in a Hearthstone Power.log.

    The local player is identified from DebugPrintEntityChoices, rather than
    assuming PlayerID=1 or PlayerID=2. Loss events are counted from
    PowerTaskList output to avoid double-counting the corresponding
    GameState/PowerTaskList debug representations.
    """
    return game_results(path).count("LOST")

def latest_start_of_game_duplicates(path: str | Path) -> list[Card]:
    """Return cards copied by the latest Start of Game effect."""
    path = Path(path)
    if not path.is_file():
        return []

    lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    latest_start = None
    for index, line in enumerate(lines):
        match = _START_OF_GAME.search(line)
        if match:
            latest_start = (index, int(match.group("entity_id")))

    if latest_start is None:
        return []

    start_index, creator_id = latest_start
    copied_ids = []
    pending_card = None
    has_creator = False
    has_copied_from = False

    for line in lines[start_index + 1:]:
        if "BLOCK_END" in line:
            break
        entity = _COPIED_ENTITY.search(line)
        if entity:
            pending_card = (entity.group("entity_id"), entity.group("card_id"))
            has_creator = False
            has_copied_from = False
            continue
        creator = _TAG_CREATOR.search(line)
        if creator and int(creator.group("creator")) == creator_id:
            has_creator = True
            if pending_card and has_copied_from:
                copied_ids.append(pending_card[1])
                pending_card = None
            continue
        copied = _TAG_COPIED.search(line)
        if copied:
            has_copied_from = True
            if pending_card and has_creator:
                copied_ids.append(pending_card[1])
                pending_card = None

    names = {}
    for line in lines:
        entity = _ENTITY.search(line)
        if entity and entity.group("card_id") in copied_ids:
            name = entity.group("name")
            if not name.startswith("UNKNOWN ENTITY"):
                names[entity.group("card_id")] = name

    return [Card(card_id, names.get(card_id)) for card_id in copied_ids]



_ENTITY_DETAILS = re.compile(
    r"(?:Entity=|Updating Entity=|Updating )\[entityName=(?P<name>.*?) id=(?P<entity_id>\d+) "
    r"zone=(?P<zone>\w+) zonePos=-?\d+ cardId=(?P<card_id>\S*) "
    r"player=(?P<player>\d+)\]"
)
_CARD_ID_UPDATE = re.compile(r"\] CardID=(?P<card_id>\S+)")
_TAG_VALUE = re.compile(r"tag=(?P<tag>CREATOR|COPIED_FROM_ENTITY_ID|ZONE) value=(?P<value>\S+)")
_UNKNOWN_PLAYERS = {"UNKNOWN HUMAN PLAYER", "UNKNOWN PLAYER"}
_PLAYER_IDENTITY = re.compile(r"PlayerID=(?P<player_id>\d+), PlayerName=(?P<player>.+?)\s*$")


def _parse_deck_effect_segment(
    lines: list[str],
    local_name: str,
) -> list[DeckEffect]:
    """Parse one game segment, where Hearthstone entity IDs are unique."""
    entities: dict[int, dict[str, object]] = {}
    local_player_id: int | None = None
    for line in lines:
        player_identity = _PLAYER_IDENTITY.search(line)
        if player_identity and player_identity.group("player").strip() == local_name:
            local_player_id = int(player_identity.group("player_id"))
            break

    current_entity_id: int | None = None
    start_of_game_sources: set[int] = set()
    for line in lines:
        start = _START_OF_GAME.search(line)
        if start:
            start_of_game_sources.add(int(start.group("entity_id")))

        descriptor = _ENTITY_DETAILS.search(line)
        if descriptor:
            entity_id = int(descriptor.group("entity_id"))
            current_entity_id = entity_id
            name = descriptor.group("name")
            card_id = descriptor.group("card_id")
            update = _CARD_ID_UPDATE.search(line)
            if update:
                card_id = update.group("card_id")
            previous = entities.get(entity_id, {})
            entities[entity_id] = {
                "name": name if name and not name.startswith("UNKNOWN ENTITY") else previous.get("name"),
                "card_id": card_id or previous.get("card_id"),
                "player": int(descriptor.group("player")),
                "zone": descriptor.group("zone"),
                "creator": previous.get("creator"),
                "copied_from": previous.get("copied_from"),
            }

        tag = _TAG_VALUE.search(line)
        if tag and current_entity_id is not None:
            entity = entities.get(current_entity_id)
            if entity is not None:
                if tag.group("tag") == "CREATOR":
                    try:
                        entity["creator"] = int(tag.group("value"))
                    except ValueError:
                        pass
                elif tag.group("tag") == "COPIED_FROM_ENTITY_ID":
                    try:
                        entity["copied_from"] = int(tag.group("value"))
                    except ValueError:
                        pass
                elif tag.group("tag") == "ZONE":
                    entity["zone"] = tag.group("value")

        if "BLOCK_END" in line:
            current_entity_id = None

    if local_player_id is None:
        return []

    effects: list[DeckEffect] = []
    for entity_id, entity in entities.items():
        if entity.get("player") != local_player_id or entity.get("zone") != "DECK":
            continue
        creator_id = entity.get("creator")
        copied_from = entity.get("copied_from")
        if not isinstance(creator_id, int) or creator_id == entity_id:
            continue
        source_entity = entities.get(creator_id)
        if source_entity is None or source_entity.get("player") != local_player_id:
            continue
        generated_id = entity.get("card_id")
        source_card_id = source_entity.get("card_id")
        if not isinstance(generated_id, str) or not generated_id:
            continue
        if not isinstance(source_card_id, str) or not source_card_id:
            continue

        source_name = source_entity.get("name")
        generated_name = entity.get("name")
        source = Card(source_card_id, source_name if isinstance(source_name, str) else None)
        generated = Card(generated_id, generated_name if isinstance(generated_name, str) else None)
        trigger = "START_OF_GAME" if creator_id in start_of_game_sources else "CARD_EFFECT"
        reason = "copied" if isinstance(copied_from, int) else "generated"
        effects.append(DeckEffect(source=source, generated=generated, trigger=trigger, reason=reason))

    return effects


def latest_deck_effects(path: str | Path) -> list[DeckEffect]:
    """Find generated/copied cards added to the local player's deck across a run.

    Power.log entity IDs are reused between games, so each Underground Arena
    game is parsed independently before effects are deduplicated by card IDs.
    """
    path = Path(path)
    if not path.is_file():
        return []

    lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    local_name = None
    for line in lines:
        identity = _LOCAL_PLAYER.search(line)
        if identity:
            candidate = identity.group("player").strip()
            if candidate not in _UNKNOWN_PLAYERS:
                local_name = candidate
                break
    if local_name is None:
        return []

    game_starts = [
        index for index, line in enumerate(lines)
        if _UNDERGROUND.search(line)
    ]
    if game_starts:
        segments = [
            lines[start:game_starts[index + 1] if index + 1 < len(game_starts) else len(lines)]
            for index, start in enumerate(game_starts)
        ]
    else:
        segments = [lines]

    unique: dict[tuple[str, str, str | None, str | None], DeckEffect] = {}
    for segment in segments:
        for effect in _parse_deck_effect_segment(segment, local_name):
            key = (
                effect.source.card_id,
                effect.generated.card_id,
                effect.trigger,
                effect.reason,
            )
            unique.setdefault(key, effect)
    return list(unique.values())
