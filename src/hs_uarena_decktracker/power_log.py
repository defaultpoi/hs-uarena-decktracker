from __future__ import annotations

import re
from pathlib import Path


_UNDERGROUND = re.compile(r"GameType=GT_UNDERGROUND_ARENA\b")


def is_underground_arena(path: str | Path) -> bool:
    """Return True only when Power.log identifies an Underground Arena game."""
    path = Path(path)
    if not path.is_file():
        return False

    with path.open("r", encoding="utf-8", errors="replace") as handle:
        return any(_UNDERGROUND.search(line) for line in handle)
