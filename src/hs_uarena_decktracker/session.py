from __future__ import annotations

from dataclasses import replace
from pathlib import Path

from .card_db import CardDatabase

from .arena_log import ArenaLogParser
from .models import ArenaRun
from .power_log import (
    game_results,
    is_underground_arena,
    latest_result,
    latest_deck_effects,
)


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
    card_db = CardDatabase()
    try:
        card_db.load()
    except (OSError, ValueError):
        card_db = None

    def enrich(card):
        if card_db is None:
            return card
        data = card_db.get(card.card_id)
        if data is None:
            return card
        return replace(
            card,
            name=card.name or data.name,
            text=card.text or data.text,
        )

    run.game_results = [
        result
        for session in matching
        for result in game_results(session / "Power.log")
    ]
    run.losses = run.game_results.count("LOST")
    for session in reversed(matching):
        result = latest_result(session / "Power.log")
        if result is not None:
            run.last_result = result
            run.deck_effects = [
                replace(effect, source=enrich(effect.source), generated=enrich(effect.generated))
                for effect in latest_deck_effects(session / "Power.log")
            ]
            run.start_of_game_duplicates = [
                effect.generated
                for effect in run.deck_effects
                if effect.trigger == "START_OF_GAME"
            ]
            break
    return run
