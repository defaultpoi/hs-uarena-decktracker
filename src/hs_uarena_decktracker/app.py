from __future__ import annotations

import sys
from pathlib import Path

from .discovery import find_log_root, latest_session
from .session import parse_session


def main() -> None:
    try:
        from PySide6.QtCore import QTimer
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
            self.setMinimumWidth(360)

            self.status = QLabel("Looking for Hearthstone logs…")
            self.deck = QListWidget()
            self.redrafts = QListWidget()

            layout = QVBoxLayout()
            layout.addWidget(self.status)
            layout.addWidget(QLabel("Current deck"))
            layout.addWidget(self.deck)
            layout.addWidget(QLabel("Redrafts"))
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
                self.status.setText("Hearthstone Logs directory not found")
                return

            session = latest_session(log_root)
            if session is None:
                self.status.setText("No Hearthstone session found")
                return

            run = parse_session(session)
            if not run.underground:
                self.status.setText("Latest session is not Underground Arena")
                return

            self.status.setText(
                f"Underground Arena  •  Deck {run.deck_id or 'unknown'}"
                f"  •  Hero {run.hero_card_id or 'unknown'}"
            )

            self.deck.clear()
            if run.current_deck:
                for card in run.current_deck.cards:
                    self.deck.addItem(card.display_name())
            else:
                self.deck.addItem("No deck snapshot yet")

            self.redrafts.clear()
            for redraft in run.redrafts:
                cards = ", ".join(card.display_name() for card in redraft.selected)
                self.redrafts.addItem(f"#{redraft.number}: {cards}")

    app = QApplication(sys.argv)
    window = Window()
    window.show()
    sys.exit(app.exec())
