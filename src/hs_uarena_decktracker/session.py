from __future__ import annotations

from pathlib import Path

from .arena_log import ArenaLogParser
from .models import ArenaRun
from .power_log import count_losses, is_underground_arena, latest_result


def parse_session(session_dir: str | Path) -> ArenaRun:
    return parse_sessions([Path(session_dir)])


def parse_sessions(session_dirs: list[str | Path]) -> ArenaRun:
    """Parse all sessions belonging to the same Arena draft deck."""
    sessions = sorted((Path(path) for path in session_dirs), key=lambda path: path.name)
    parser = ArenaLogParser()

    parsed = [
        (session, parser.parse(session / "Arena.log"))
        for session in sessions
    ]
    parsed = [(session, run) for session, run in parsed if run.deck_id]

    if not parsed:
        return ArenaRun()

    target_deck_id = parsed[-1][1].deck_id
    matching = [
        session
        for session, run in parsed
        if run.deck_id == target_deck_id
    ]

    run = parser.parse_many([session / "Arena.log" for session in matching])
    run.underground = any(
        is_underground_arena(session / "Power.log")
        for session in matching
    )
    run.losses = sum(count_losses(session / "Power.log") for session in matching)
    for session in reversed(matching):
        result = latest_result(session / "Power.log")
        if result is not None:
            run.last_result = result
            break
    return run
