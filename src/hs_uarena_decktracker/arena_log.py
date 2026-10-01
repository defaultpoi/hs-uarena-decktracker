from __future__ import annotations

import re
from collections import Counter
from pathlib import Path

from .models import ArenaRun, Card, DeckSnapshot, Redraft


_DRAFT_HEADER = re.compile(
    r"(?P<ts>\d{2}:\d{2}:\d{2}\.\d+) "
    r"DraftManager\.OnChoicesAndContents - Draft Deck ID: (?P<deck>\d+), "
    r"Hero Card = (?P<hero>\S+)"
)

_DECK_CARD = re.compile(
    r"(?P<ts>\d{2}:\d{2}:\d{2}\.\d+) "
    r"DraftManager\.OnChoicesAndContents - Draft deck contains card (?P<card>\S+)"
)

_MODE = re.compile(
    r"(?P<ts>\d{2}:\d{2}:\d+\.\d+) SetDraftMode - (?P<mode>\S+)"
)

_CHOICE = re.compile(
    r"(?P<ts>\d{2}:\d{2}:\d+\.\d+) Client chooses: "
    r"(?P<name>.*?) \((?P<card>[^)]+)\)"
)


class ArenaLogParser:
    """Parse the Arena.log format used by Underground Arena."""

    def parse(self, path: str | Path) -> ArenaRun:
        run = ArenaRun()
        path = Path(path)

        if not path.is_file():
            return run

        snapshot_ts: str | None = None
        snapshot_cards: list[Card] = []
        redraft_number = 0
        redraft_started: str | None = None
        redraft_selected: list[Card] = []

        def finish_snapshot() -> None:
            nonlocal snapshot_ts, snapshot_cards
            if run.deck_id and snapshot_ts is not None and snapshot_cards:
                run.deck_snapshots.append(
                    DeckSnapshot(
                        timestamp=snapshot_ts,
                        deck_id=run.deck_id,
                        cards=tuple(snapshot_cards),
                    )
                )
            snapshot_ts = None
            snapshot_cards = []

        def finish_redraft(ended_at: str | None) -> None:
            nonlocal redraft_started, redraft_selected
            if redraft_started is not None:
                run.redrafts.append(
                    Redraft(
                        number=redraft_number,
                        started_at=redraft_started,
                        selected=tuple(redraft_selected),
                        ended_at=ended_at,
                    )
                )
            redraft_started = None
            redraft_selected = []

        for raw_line in path.read_text(encoding="utf-8", errors="replace").splitlines():
            line = raw_line.strip()

            header = _DRAFT_HEADER.search(line)
            if header:
                finish_snapshot()
                run.deck_id = header.group("deck")
                run.hero_card_id = header.group("hero")
                snapshot_ts = header.group("ts")
                continue

            card_match = _DECK_CARD.search(line)
            if card_match:
                if snapshot_ts is None:
                    snapshot_ts = card_match.group("ts")
                snapshot_cards.append(Card(card_match.group("card")))
                continue

            mode = _MODE.search(line)
            if mode:
                mode_name = mode.group("mode")
                if mode_name == "REDRAFTING":
                    finish_snapshot()
                    redraft_number += 1
                    redraft_started = mode.group("ts")
                    redraft_selected = []
                elif mode_name == "ACTIVE_DRAFT_DECK":
                    finish_redraft(mode.group("ts"))
                continue

            choice = _CHOICE.search(line)
            if choice and redraft_started is not None:
                redraft_selected.append(
                    Card(choice.group("card"), choice.group("name"))
                )

        finish_snapshot()
        if redraft_started is not None:
            finish_redraft(None)

        self._infer_discards(run)
        return run

    @staticmethod
    def _infer_discards(run: ArenaRun) -> None:
        """Infer definitely removed cards by comparing surrounding snapshots."""
        snapshots = run.deck_snapshots

        for redraft in run.redrafts:
            if redraft.ended_at is None:
                continue

            before = next(
                (
                    snapshot
                    for snapshot in reversed(snapshots)
                    if snapshot.timestamp < redraft.started_at
                ),
                None,
            )
            after = next(
                (
                    snapshot
                    for snapshot in snapshots
                    if snapshot.timestamp > redraft.ended_at
                ),
                None,
            )

            if before is None or after is None:
                continue

            before_counts = Counter(card.card_id for card in before.cards)
            after_counts = Counter(card.card_id for card in after.cards)
            removed = before_counts - after_counts

            redraft.discarded = tuple(
                Card(card_id)
                for card_id, count in removed.items()
                for _ in range(count)
            )
            redraft.discarded_complete = sum(removed.values()) == 5
