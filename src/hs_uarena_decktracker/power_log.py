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
                    local_player = choice.group("player")
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
