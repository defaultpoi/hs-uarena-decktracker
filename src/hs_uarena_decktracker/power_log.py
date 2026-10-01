from __future__ import annotations

import re
from pathlib import Path


_UNDERGROUND = re.compile(r"GameType=GT_UNDERGROUND_ARENA\b")
_LOCAL_PLAYER = re.compile(
    r"GameState\.DebugPrintEntityChoices\(\) - .*Player=(?P<player>.+?) TaskList="
)
_RESULT = re.compile(
    r"PowerTaskList\.DebugPrintPower\(\) - .*"
    r"Entity=(?P<player>.+?) tag=PLAYSTATE value=(?P<result>LOST|WON)\b"
)


def is_underground_arena(path: str | Path) -> bool:
    """Return True only when Power.log identifies an Underground Arena game."""
    path = Path(path)
    if not path.is_file():
        return False

    with path.open("r", encoding="utf-8", errors="replace") as handle:
        return any(_UNDERGROUND.search(line) for line in handle)


def latest_result(path: str | Path) -> str | None:
    """Return the latest terminal result for the local player, if known."""
    path = Path(path)
    if not path.is_file():
        return None
    local_player: str | None = None
    result: str | None = None
    with path.open("r", encoding="utf-8", errors="replace") as handle:
        for line in handle:
            if local_player is None:
                choice = _LOCAL_PLAYER.search(line)
                if choice:
                    local_player = choice.group("player")
            if local_player is not None:
                match = _RESULT.search(line)
                if match and match.group("player") == local_player:
                    result = match.group("result")
    return result


def count_losses(path: str | Path) -> int:
    """Count losses for the local player in a Hearthstone Power.log.

    The local player is identified from DebugPrintEntityChoices, rather than
    assuming PlayerID=1 or PlayerID=2. Loss events are counted from
    PowerTaskList output to avoid double-counting the corresponding
    GameState/PowerTaskList debug representations.
    """
    path = Path(path)
    if not path.is_file():
        return 0

    local_player: str | None = None
    losses = 0

    with path.open("r", encoding="utf-8", errors="replace") as handle:
        for line in handle:
            if local_player is None:
                choice = _LOCAL_PLAYER.search(line)
                if choice:
                    local_player = choice.group("player")

            if local_player is not None:
                result = _RESULT.search(line)
                if result and result.group("player") == local_player and result.group("result") == "LOST":
                    losses += 1

    return losses
