from __future__ import annotations

import re
from pathlib import Path

from .models import Card


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
