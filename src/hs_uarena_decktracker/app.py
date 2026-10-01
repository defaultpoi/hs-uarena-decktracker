from __future__ import annotations

import sys
from pathlib import Path

from .discovery import find_log_root, sessions
from .models import ArenaRun, Redraft
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
            self.setFixedWidth(420)
            self.setWindowFlag(Qt.WindowType.WindowStaysOnTopHint, True)
            self._log_fingerprint: tuple[tuple[str, int, int], ...] | None = None
            self._cached_run: ArenaRun | None = None

            self.status = QLabel("Looking for Hearthstone logs…")
            self.status.setWordWrap(True)

            self.deck_label = QLabel("Current deck")
            self.deck = QListWidget()

            self.redraft_label = QLabel("Redraft history")
            self.redrafts = QListWidget()

            layout = QVBoxLayout()
            layout.setContentsMargins(8, 8, 8, 8)
            layout.setSpacing(6)
            layout.addWidget(self.status)
            layout.addWidget(self.deck_label)
            layout.addWidget(self.deck)
            layout.addWidget(self.redraft_label)
            layout.addWidget(self.redrafts)

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
                return

            session_dirs = sessions(log_root)
            if not session_dirs:
                self._log_fingerprint = None
                self._cached_run = None
                self.status.setText("No Hearthstone session found")
                self.deck.clear()
                self.redrafts.clear()
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
                return

            deck = run.current_deck
            deck_count = len(deck.cards) if deck else 0
            self.status.setText(
                f"Underground Arena  •  {deck_count}/30 cards"
                f"  •  Hero {run.hero_card_id or 'unknown'}"
            )

            self.deck.clear()
            if deck:
                for card in deck.cards:
                    self.deck.addItem(card.display_name())
            else:
                self.deck.addItem("No deck snapshot yet")

            self.redrafts.clear()
            if run.redrafts:
                for redraft in run.redrafts:
                    self.redrafts.addItem(format_redraft(redraft))
            else:
                self.redrafts.addItem("No redrafts yet")


    app = QApplication(sys.argv)
    window = Window()
    window.show()
    sys.exit(app.exec())
