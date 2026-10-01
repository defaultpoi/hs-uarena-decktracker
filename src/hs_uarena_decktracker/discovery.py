from __future__ import annotations

import os
from pathlib import Path


def find_log_root() -> Path | None:
    """Find the Hearthstone Logs directory on a typical Linux/Wine install."""
    explicit = os.environ.get("HS_LOG_DIR")
    if explicit:
        path = Path(explicit).expanduser()
        return path if path.is_dir() else None

    home = Path.home()
    candidates = [
        home / "Games/battlenet/drive_c/Program Files (x86)/Hearthstone/Logs",
        home / "Games/Hearthstone/drive_c/Program Files (x86)/Hearthstone/Logs",
        home / ".wine/drive_c/Program Files (x86)/Hearthstone/Logs",
    ]
    for path in candidates:
        if path.is_dir():
            return path
    return None


def sessions(log_root: Path) -> list[Path]:
    """Return Hearthstone session directories in chronological name order."""
    return sorted(
        (path for path in log_root.glob("Hearthstone_*") if path.is_dir()),
        key=lambda path: path.name,
    )


def latest_session(log_root: Path) -> Path | None:
    found = sessions(log_root)
    return found[-1] if found else None
