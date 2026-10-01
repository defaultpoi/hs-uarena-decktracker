from __future__ import annotations

import sys
from collections import Counter
from pathlib import Path

from .discovery import find_log_root, sessions
from .models import ArenaRun, Card, Redraft
from .session import parse_sessions


def format_redraft(redraft: Redraft) -> str:
    selected = ", ".join(card.display_name() for card in redraft.selected) or "none"

    if redraft.ended_at is None:
        return f"#{redraft.number}  IN PROGRESS  •  selected: {selected}"

    if redraft.discarded:
        discarded = ", ".join(card.display_name() for card in redraft.discarded)
        suffix = "" if redraft.discarded_complete else "  •  partial"
        return f"#{redraft.number}  selected: {selected}  •  discarded: {discarded}{suffix}"

    return f"#{redraft.number}  selected: {selected}  •  discarded: not determined"


def redraft_state(redraft: Redraft) -> str:
    """Format the latest redraft as a compact two-line status block."""
    selected = ", ".join(card.display_name() for card in redraft.selected) or "none"
    selected_count = len(redraft.selected)

    if redraft.ended_at is None:
        return (
            f"REDRAFT #{redraft.number} — IN PROGRESS\n"
            f"Selected ({selected_count}/5): {selected}\n"
            "Discarded: waiting for resulting deck"
        )

    if redraft.discarded:
        discarded = ", ".join(card.display_name() for card in redraft.discarded)
        discarded_count = len(redraft.discarded)
        status = "complete" if redraft.discarded_complete else "partial"
        return (
            f"REDRAFT #{redraft.number}\n"
            f"Selected ({selected_count}/5): {selected}\n"
            f"Discarded ({discarded_count}/5, {status}): {discarded}"
        )

    return (
        f"REDRAFT #{redraft.number}\n"
        f"Selected ({selected_count}/5): {selected}\n"
        "Discarded (0/5): not determined"
    )


def format_run_status(run: ArenaRun, deck_count: int) -> str:
    """Format the compact run summary shown above the deck."""
    progress = "RUN COMPLETE" if run.run_ended else f"{run.losses}/3 losses"
    result = run.last_result or "—"
    hero = run.hero_card_id or "unknown"
    return f"UNDERGROUND ARENA  •  {progress}\n{deck_count} cards  •  Last: {result}  •  Hero: {hero}"


def format_run_progress(run: ArenaRun) -> str:
    """Format the ordered game/redraft progression without inventing timestamps."""
    lines: list[str] = []

    for index, result in enumerate(run.game_results, start=1):
        lines.append(f"GAME #{index}: {result}")
        if result == "LOST" and index <= len(run.redrafts):
            lines.append(f"  ↳ REDRAFT #{index}")

    if not lines:
        return "No games recorded"

    if run.run_ended:
        lines.append("RUN COMPLETE")

    return "\n".join(lines)


def format_deck(cards: tuple[Card, ...]) -> str:
    """Format a deck compactly, grouping duplicate cards."""
    names: dict[str, str] = {}
    counts: Counter[str] = Counter()

    for card in cards:
        if card.card_id not in names or card.name is not None:
            names[card.card_id] = card.display_name()
        counts[card.card_id] += 1

    return "\n".join(
        f"{names[card_id]} ×{count}" if count > 1 else names[card_id]
        for card_id, count in counts.items()
    ) or "No deck snapshot yet"


def log_fingerprint(session_dirs: list[str | Path]) -> tuple[tuple[str, int, int], ...]:
    """Return a cheap fingerprint for the log files used by the live GUI."""
    fingerprint: list[tuple[str, int, int]] = []

    for session_dir in session_dirs:
        session = Path(session_dir)
        for filename in ("Arena.log", "Power.log"):
            path = session / filename
            try:
                stat = path.stat()
            except FileNotFoundError:
                fingerprint.append((str(path), 0, 0))
            else:
                fingerprint.append((str(path), stat.st_mtime_ns, stat.st_size))

    return tuple(fingerprint)


def main() -> None:
    try:
        from PySide6.QtCore import QTimer, Qt
        from PySide6.QtWidgets import (
            QApplication,
            QLabel,
            QListWidget,
            QMainWindow,
            QPlainTextEdit,
            QVBoxLayout,
            QWidget,
        )
    except ImportError as exc:
        raise SystemExit(
            "PySide6 is required for the GUI. Install with: "
            "pip install -e '.[gui]'"
        ) from exc

    class Window(QMainWindow):
        def __init__(self) -> None:
            super().__init__()
            self.setWindowTitle("HS Underground Arena")
            self.setFixedSize(380, 560)
            self.setWindowFlag(Qt.WindowType.WindowStaysOnTopHint, True)
            self._log_fingerprint: tuple[tuple[str, int, int], ...] | None = None
            self._cached_run: ArenaRun | None = None

            self.status = QLabel("Looking for Hearthstone logs…")
            self.status.setWordWrap(True)
            self.status.setAlignment(Qt.AlignmentFlag.AlignCenter)

            self.deck_label = QLabel("CURRENT DECK")
            self.deck_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self.deck = QPlainTextEdit()
            self.deck.setReadOnly(True)
            self.deck.setMaximumHeight(300)
            self.deck.setLineWrapMode(QPlainTextEdit.LineWrapMode.NoWrap)

            self.redraft_label = QLabel("REDRAFT STATUS")
            self.redraft_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self.redraft_current = QLabel("No redrafts yet")
            self.redraft_current.setWordWrap(True)
            self.redraft_current.setTextInteractionFlags(
                Qt.TextInteractionFlag.TextSelectableByMouse
            )
            self.redrafts = QListWidget()
            self.redrafts.setMaximumHeight(130)

            self.progress_label = QLabel("RUN PROGRESS")
            self.progress_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self.progress = QLabel("No games recorded")
            self.progress.setWordWrap(True)
            self.progress.setTextInteractionFlags(
                Qt.TextInteractionFlag.TextSelectableByMouse
            )

            layout = QVBoxLayout()
            layout.setContentsMargins(8, 8, 8, 8)
            layout.setSpacing(4)
            layout.addWidget(self.status)
            layout.addWidget(self.deck_label)
            layout.addWidget(self.deck)
            layout.addWidget(self.redraft_label)
            layout.addWidget(self.redraft_current)
            layout.addWidget(self.redrafts)
            layout.addWidget(self.progress_label)
            layout.addWidget(self.progress)

            root = QWidget()
            root.setLayout(layout)
            self.setCentralWidget(root)

            self.timer = QTimer(self)
            self.timer.timeout.connect(self.refresh)
            self.timer.start(1000)
            self.refresh()

        def refresh(self) -> None:
            log_root = find_log_root()
            if log_root is None:
                self._log_fingerprint = None
                self._cached_run = None
                self.status.setText("Hearthstone Logs directory not found")
                self.deck.clear()
                self.redrafts.clear()
                self.redraft_current.setText("No redrafts yet")
                self.progress.setText("No games recorded")
                return

            session_dirs = sessions(log_root)
            if not session_dirs:
                self._log_fingerprint = None
                self._cached_run = None
                self.status.setText("No Hearthstone session found")
                self.deck.clear()
                self.redrafts.clear()
                self.redraft_current.setText("No redrafts yet")
                self.progress.setText("No games recorded")
                return

            fingerprint = log_fingerprint(session_dirs)
            if fingerprint != self._log_fingerprint:
                self._cached_run = parse_sessions(session_dirs)
                self._log_fingerprint = fingerprint

            run = self._cached_run
            if run is None:
                return
            if not run.underground:
                self.status.setText("Latest run is not Underground Arena")
                self.deck.clear()
                self.redrafts.clear()
                self.redraft_current.setText("No redrafts yet")
                self.progress.setText("No games recorded")
                return

            deck = run.current_deck
            deck_count = len(deck.cards) if deck else 0
            self.status.setText(format_run_status(run, deck_count))

            self.deck.clear()
            self.deck.setPlainText(format_deck(deck.cards) if deck else "No deck snapshot yet")

            self.redrafts.clear()
            if run.redrafts:
                self.redraft_current.setText(redraft_state(run.redrafts[-1]))
                if len(run.redrafts) > 1:
                    self.redrafts.addItem("HISTORY")
                    for redraft in reversed(run.redrafts[:-1]):
                        self.redrafts.addItem(format_redraft(redraft))
            else:
                self.redraft_current.setText("No redrafts yet")

            self.progress.setText(format_run_progress(run))


    app = QApplication(sys.argv)
    window = Window()
    window.show()
    sys.exit(app.exec())
