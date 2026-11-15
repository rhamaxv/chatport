"""Live checks for the Connect and Prepare pages. Pure functions; the UI runs them on a worker thread."""
from __future__ import annotations

import shutil
from collections.abc import Callable
from pathlib import Path

MIN_FREE_BYTES = 2 * 1024 ** 3


def free_bytes(path: Path) -> int:
    probe = Path(path)
    while not probe.exists() and probe.parent != probe:
        probe = probe.parent
    try:
        return shutil.disk_usage(probe).free
    except OSError:
        return 0


def connect_checks(engine, adb_path: str | None, work_root: Path, platform_check: Callable[[], dict]) -> dict:
    android = engine.android_status() if adb_path else {"state": "no_adb"}
    return {
        "android": android,
        "iphone": engine.iphone_status(),
        "computer": {"free_bytes": free_bytes(work_root), "adb": adb_path, "platform": platform_check()},
    }


def ready_checks(engine) -> dict:
    return {"iphone": engine.iphone_status(with_apps=True)}


def is_ready(result: dict) -> bool:
    android = result.get("android") or {}
    iphone = result.get("iphone") or {}
    computer = result.get("computer") or {}
    platform = computer.get("platform") or {}
    return (
        android.get("state") == "ready"
        and android.get("backup") == "ok"
        and iphone.get("state") == "ready"
        and platform.get("state") == "ok"
        and bool(computer.get("adb"))
        and (computer.get("free_bytes") or 0) > MIN_FREE_BYTES
    )
