from __future__ import annotations

import re
from collections import Counter
from dataclasses import replace
from pathlib import Path

from .models import ArenaRun, Card, DeckSnapshot, Redraft


_DRAFT_HEADER = re.compile(
    r"(?P<ts>\d{2}:\d{2}:\d{2}\.\d+) "
    r"DraftManager\.OnChoicesAndContents - Draft Deck ID: (?P<deck>\d+), "
    r"Hero Card = (?P<hero>\S+)"
)

_DECK_CARD = re.compile(
    r"(?P<ts>\d{2}:\d{2}:\d+\.\d+) "
    r"DraftManager\.OnChoicesAndContents - Draft deck contains card (?P<card>\S+)"
)

_MODE = re.compile(
    r"(?P<ts>\d{2}:\d{2}:\d+\.\d+) SetDraftMode - (?P<mode>\S+)"
)

_REDRAFT_BEGIN = re.compile(
    r"(?P<ts>\d{2}:\d{2}:\d+\.\d+) DraftManager\.OnRedraftBegin - Got new redraft deck with ID: (?P<deck>\d+)"
)

_CHOICE = re.compile(
    r"(?P<ts>\d{2}:\d{2}:\d+\.\d+) Client chooses: "
    r"(?P<name>.*?) \((?P<card>[^)]+)\)"
)


class ArenaLogParser:
    """Parse the Arena.log format used by Underground Arena."""

    def parse(self, path: str | Path) -> ArenaRun:
        path = Path(path)
        if not path.is_file():
            return ArenaRun()
        return self._parse_lines(
            path.read_text(encoding="utf-8", errors="replace").splitlines()
        )

    def parse_many(self, paths: list[str | Path]) -> ArenaRun:
        lines: list[str] = []
        for path in paths:
            path = Path(path)
            if path.is_file():
                lines.extend(
                    path.read_text(encoding="utf-8", errors="replace").splitlines()
                )
        return self._parse_lines(lines)

    def _parse_lines(self, lines: list[str]) -> ArenaRun:
        run = ArenaRun()

        snapshot_ts: str | None = None
        snapshot_cards: list[Card] = []
        redraft_number = 0
        redraft_started: str | None = None
        redraft_deck_id: str | None = None
        redraft_selected: list[Card] = []
        redraft_before_snapshot_indices: list[int] = []
        redraft_after_snapshot_starts: list[int] = []

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
            nonlocal redraft_started, redraft_deck_id, redraft_selected
            if redraft_started is not None:
                run.redrafts.append(
                    Redraft(
                        number=redraft_number,
                        started_at=redraft_started,
                        redraft_deck_id=redraft_deck_id,
                        selected=tuple(redraft_selected),
                        ended_at=ended_at,
                    )
                )
                # The next deck snapshot belongs to the resulting deck. Any
                # later snapshots may reflect ordinary gameplay mutations.
                redraft_after_snapshot_starts.append(len(run.deck_snapshots))
            redraft_started = None
            redraft_deck_id = None
            redraft_selected = []

        for raw_line in lines:
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

            redraft_begin = _REDRAFT_BEGIN.search(line)
            if redraft_begin and redraft_started is not None:
                redraft_deck_id = redraft_begin.group("deck")
                continue

            mode = _MODE.search(line)
            if mode:
                mode_name = mode.group("mode")
                if mode_name == "REDRAFTING":
                    finish_snapshot()
                    redraft_before_snapshot_indices.append(len(run.deck_snapshots) - 1)
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

        self._infer_discards(
            run,
            redraft_before_snapshot_indices,
            redraft_after_snapshot_starts,
        )
        return run

    @staticmethod
    def _infer_discards(
        run: ArenaRun,
        redraft_before_snapshot_indices: list[int],
        redraft_after_snapshot_starts: list[int],
    ) -> None:
        """Infer removed cards using log order rather than wall-clock time.

        Session logs reset their time-of-day clock, so comparing timestamp
        strings can associate a redraft with the wrong snapshot when a run
        spans sessions or midnight. Snapshot order is stable across the
        combined Arena.log files.
        """
        snapshots = run.deck_snapshots
        inferred: list[Redraft] = []

        for index, redraft in enumerate(run.redrafts):
            if redraft.ended_at is None:
                inferred.append(redraft)
                continue

            before_index = (
                redraft_before_snapshot_indices[index]
                if index < len(redraft_before_snapshot_indices)
                else -1
            )
            before = (
                snapshots[before_index]
                if 0 <= before_index < len(snapshots)
                else None
            )

            after_start = (
                redraft_after_snapshot_starts[index]
                if index < len(redraft_after_snapshot_starts)
                else len(snapshots)
            )
            # Use the first snapshot after ACTIVE_DRAFT_DECK. Later snapshots
            # may include ordinary gameplay mutations such as shuffled cards.
            after = (
                snapshots[after_start]
                if after_start < len(snapshots)
                else None
            )

            if before is None or after is None:
                inferred.append(redraft)
                continue

            before_counts = Counter(card.card_id for card in before.cards)
            after_counts = Counter(card.card_id for card in after.cards)
            removed = before_counts - after_counts

            # The redraft choices carry names, while deck snapshots currently
            # expose only card IDs. Reuse those names when a selected card is
            # also discarded so the UI/CLI can show useful names immediately.
            selected_names = {
                card.card_id: card.name
                for card in redraft.selected
                if card.name is not None
            }
            discarded = tuple(
                Card(card_id, selected_names.get(card_id))
                for card_id, count in removed.items()
                for _ in range(count)
            )
            inferred.append(
                replace(
                    redraft,
                    discarded=discarded,
                    discarded_complete=(\n                        len(redraft.selected) == 5\n                        and sum(removed.values()) == 5\n                    ),
                )
            )

        run.redrafts = inferred
