from __future__ import annotations

import argparse
import json
from pathlib import Path

from .discovery import sessions
from .session import parse_sessions


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Parse a Hearthstone Underground Arena log session."
    )
    parser.add_argument("session", help="Hearthstone_YYYY_MM_DD_HH_MM_SS directory")
    args = parser.parse_args()

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
