from __future__ import annotations

from pathlib import Path

from .arena_log import ArenaLogParser
from .card_db import CardDatabase
from .deck_state import latest_deck_removals
from .effects import latest_deck_effects
from .models import ArenaRun
from .power_log import (
    game_results,
    is_underground_arena,
    latest_result,
    latest_start_of_game_duplicates,
)


def parse_session(session_dir: str | Path) -> ArenaRun:
    return parse_sessions([Path(session_dir)])


def parse_sessions(session_dirs: list[str | Path]) -> ArenaRun:
    """Parse all sessions belonging to the same Arena draft deck."""
    sessions = sorted((Path(path) for path in session_dirs), key=lambda path: path.name)
    parser = ArenaLogParser()
    database = CardDatabase()
    if database.cache_path.is_file():
        database.load()

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
    run.game_results = [
        result
        for session in matching
        for result in game_results(session / "Power.log")
    ]
    run.losses = run.game_results.count("LOST")

    for session in reversed(matching):
        power_log = session / "Power.log"
        if not power_log.is_file():
            continue

        result = latest_result(power_log)
        if result is not None:
            run.last_result = result

        run.start_of_game_duplicates = latest_start_of_game_duplicates(power_log)
        run.deck_effects = latest_deck_effects(power_log, database)
        run.generated_deck_cards = [effect.card for effect in run.deck_effects]
        if run.current_deck is not None:
            run.deck_removals = latest_deck_removals(
                power_log,
                run.current_deck.cards,
            )
        break

    return run
