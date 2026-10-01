from __future__ import annotations

import argparse
import json

from .session import parse_session


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Parse a Hearthstone Underground Arena log session."
    )
    parser.add_argument("session", help="Hearthstone_YYYY_MM_DD_HH_MM_SS directory")
    args = parser.parse_args()

    run = parse_session(args.session)

    result = {
        "underground_arena": run.underground,
        "deck_id": run.deck_id,
        "hero_card_id": run.hero_card_id,
        "losses": run.losses,
        "run_ended": run.run_ended,
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
