"""Where Chatport keeps its data on each OS. Directories are created lazily, private to the user."""
from __future__ import annotations

import os
import sys
from pathlib import Path

ENV_OVERRIDE = "CHATPORT_DATA_DIR"


def _default_data_dir() -> Path:
    if sys.platform == "darwin":
        return Path.home() / "Library" / "Application Support" / "Chatport"
    if sys.platform == "win32":
        base = os.environ.get("LOCALAPPDATA") or str(Path.home() / "AppData" / "Local")
        return Path(base) / "Chatport"
    base = os.environ.get("XDG_DATA_HOME") or str(Path.home() / ".local" / "share")
    return Path(base) / "chatport"


def _ensure(path: Path) -> Path:
    if not path.is_dir():
        path.mkdir(parents=True, exist_ok=True)
        try:
            path.chmod(0o700)
        except OSError:
            pass
    return path


def data_dir() -> Path:
    override = os.environ.get(ENV_OVERRIDE)
    return _ensure(Path(override) if override else _default_data_dir())


def log_dir() -> Path:
    return _ensure(data_dir() / "logs")


def work_dir() -> Path:
    return _ensure(data_dir() / "work")


def state_file() -> Path:
    return work_dir() / "state.json"


def adb_dir() -> Path:
    return _ensure(data_dir() / "platform-tools")
