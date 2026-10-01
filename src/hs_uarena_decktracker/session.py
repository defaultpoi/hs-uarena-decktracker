from __future__ import annotations

from pathlib import Path

from .arena_log import ArenaLogParser
from .models import ArenaRun
from .power_log import is_underground_arena


def parse_session(session_dir: str | Path) -> ArenaRun:
    session_dir = Path(session_dir)
    run = ArenaLogParser().parse(session_dir / "Arena.log")
    run.underground = is_underground_arena(session_dir / "Power.log")
    return run
