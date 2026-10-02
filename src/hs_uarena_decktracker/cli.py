from __future__ import annotations

import argparse
import json
from pathlib import Path

from .card_db import CardDatabase
from .discovery import sessions
from .session import parse_sessions


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Parse a Hearthstone Underground Arena log session."
    )
    parser.add_argument("session", nargs="?", help="Hearthstone_YYYY_MM_DD_HH_MM_SS directory")
    parser.add_argument("--update-cards", action="store_true", help="download the latest full Hearthstone card database")
    args = parser.parse_args()

    if args.update_cards:
        count = CardDatabase().update()
        print(f"Updated Hearthstone card database: {count} cards")
        if not args.session:
            return

    if not args.session:
        parser.error("session is required unless --update-cards is used")

    session = Path(args.session).expanduser()
    if not session.is_dir():
        parser.error(f"session directory not found: {session}")

    history = [path for path in sessions(session.parent) if path.name <= session.name]
    run = parse_sessions(history)

    result = {
        "underground_arena": run.underground,
        "deck_id": run.deck_id,
        "hero_card_id": run.hero_card_id,
        "losses": run.losses,
        "run_ended": run.run_ended,
        "last_result": run.last_result,
        "game_results": run.game_results,
        "effective_deck": [
            {"id": card.card_id, "name": card.name, "text": card.text}
            for card in run.effective_deck
        ],
        "deck_effects": [
            {\n                "card": {"id": effect.card.card_id, "name": effect.card.name, "text": effect.card.text},\n                "source_card": {"id": effect.source_card.card_id, "name": effect.source_card.name, "text": effect.source_card.text},\n                "trigger": effect.trigger,\n                "event": effect.event,\n                "reason": effect.reason,\n                "entity_id": effect.entity_id,\n                "source_entity_id": effect.source_entity_id,\n                "game_index": effect.game_index,\n            }\n            for effect in run.deck_effects\n        ],
        "deck_snapshots": [
            {
                "timestamp": snapshot.timestamp,
                "cards": [
                    {"id": card.card_id, "name": card.name}
                    for card in snapshot.cards
                ],
            }
            for snapshot in run.deck_snapshots
        ],
        "redrafts": [
            {
                "number": redraft.number,
                "started_at": redraft.started_at,
                "redraft_deck_id": redraft.redraft_deck_id,
                "ended_at": redraft.ended_at,
                "selected": [
                    {"id": card.card_id, "name": card.name}
                    for card in redraft.selected
                ],
                "discarded": [
                    {"id": card.card_id, "name": card.name}
                    for card in redraft.discarded
                ],
                "discarded_complete": redraft.discarded_complete,
            }
            for redraft in run.redrafts
        ],
    }

    print(json.dumps(result, indent=2))
