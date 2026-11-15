"""Render every wizard page with the fake runner, in light and dark, to docs/screenshots/*.png.

    .venv/bin/python tools/screens.py            # all pages, both themes
    .venv/bin/python tools/screens.py 6 9        # only names starting with 6 or 9

Runs offscreen, so no window appears. Each page is driven to the same state the README shows.
"""
from __future__ import annotations

import os
import sys
import tempfile
import time
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "tests"))

from PySide6.QtCore import Qt  # noqa: E402
from PySide6.QtWidgets import QApplication  # noqa: E402

from chatport import i18n  # noqa: E402
from chatport.app import load_fonts  # noqa: E402
from chatport.core.state import State  # noqa: E402
from chatport.ui import theme  # noqa: E402
from chatport.ui.window import MainWindow  # noqa: E402
from fake_runner import RESULTS, FakeRunner, fake_checks, fake_checks_missing, fake_ready_checks  # noqa: E402

OUT = ROOT / "docs" / "screenshots"
SIZE = (1080, 720)
KEY = "0123456789abcdef" * 4
STEPS_BEFORE = {
    "welcome": (), "connect": ("welcome",), "key": ("welcome", "connect"),
    "copy": ("welcome", "connect", "key"), "prepare": ("welcome", "connect", "key", "copy"),
    "backup": ("welcome", "connect", "key", "copy", "prepare"),
    "build": ("welcome", "connect", "key", "copy", "prepare", "backup"),
    "restore": ("welcome", "connect", "key", "copy", "prepare", "backup", "build"),
    "done": ("welcome", "connect", "key", "copy", "prepare", "backup", "build", "restore"),
}
# Stats the earlier steps would have saved, so the Done summary has numbers to show.
SAVED = {"copy": RESULTS["copy"], "build": RESULTS["build"], "backup": RESULTS["backup"]}


def wait_until(app: QApplication, predicate, timeout_s: float = 5.0) -> None:
    deadline = time.monotonic() + timeout_s
    while not predicate():
        app.processEvents()
        time.sleep(0.01)
        if time.monotonic() > deadline:
            raise TimeoutError("waited too long")


def settle(app: QApplication, ms: int = 120) -> None:
    deadline = time.monotonic() + ms / 1000
    while time.monotonic() < deadline:
        app.processEvents()
        time.sleep(0.005)


def build(app: QApplication, tmp: Path, step: str, *, checks=fake_checks, language="en",
          interval_ms=30, script: dict | None = None, existing_age=None) -> tuple[MainWindow, FakeRunner, State]:
    runner = FakeRunner(interval_ms=interval_ms)
    runner.script.update(script or {})
    if existing_age is not None:
        runner.existing_age = existing_age
    state_path = tmp / f"state-{step}-{language}-{int(time.time() * 1000)}.json"
    state = State(state_path).load()
    for earlier in STEPS_BEFORE[step]:
        state.mark(earlier, **SAVED.get(earlier, {}))
    window = MainWindow(runner, state, checks, language, ready_checks_fn=fake_ready_checks,
                        cleanup=lambda also: None, log_path=tmp / "chatport.log")
    window.resize(*SIZE)
    window.show()
    settle(app)
    return window, runner, state


def save(app: QApplication, window: MainWindow, name: str, dark: bool) -> Path:
    settle(app, 150)
    path = OUT / f"{name}-{'dark' if dark else 'light'}.png"
    window.grab().save(str(path), "PNG")
    return path


def render_all(app: QApplication, tmp: Path, dark: bool, only: list[str]) -> list[Path]:
    theme.apply(app, dark)
    written: list[Path] = []

    def wanted(name: str) -> bool:
        return not only or any(name.startswith(prefix) for prefix in only)

    def emit(window: MainWindow, name: str) -> None:
        written.append(save(app, window, name, dark))
        window.close()

    if wanted("1-welcome"):
        window, _r, _s = build(app, tmp, "welcome")
        emit(window, "1-welcome")

    if wanted("2-connect"):
        window, _r, _s = build(app, tmp, "connect")
        page = window.pages["connect"]
        wait_until(app, lambda: bool(page.result))
        emit(window, "2-connect")

    if wanted("2-connect-missing-id"):
        window, _r, _s = build(app, tmp, "connect", checks=fake_checks_missing, language="id")
        page = window.pages["connect"]
        wait_until(app, lambda: bool(page.result))
        emit(window, "2-connect-missing-id")

    if wanted("3-key"):
        window, _r, _s = build(app, tmp, "key")
        grid = window.pages["key"].grid
        grid.paste(" ".join(KEY[i:i + 4] for i in range(0, 64, 4)))
        grid.boxes[-1].setFocus(Qt.FocusReason.MouseFocusReason)
        emit(window, "3-key")

    if wanted("4-copy"):
        window, _r, _s = build(app, tmp, "copy")
        page = window.pages["copy"]
        wait_until(app, lambda: page.result is not None)
        emit(window, "4-copy")

    if wanted("5-prepare-empty"):
        window, _r, _s = build(app, tmp, "prepare")
        emit(window, "5-prepare-empty")

    if wanted("5-prepare"):
        window, _r, _s = build(app, tmp, "prepare")
        page = window.pages["prepare"]
        page.check_iphone()
        wait_until(app, lambda: page.checklist.rows["find_my"].live is True)
        page.checklist.rows["whatsapp"].box.setChecked(True)
        page.checklist.rows["airplane"].box.setChecked(True)
        emit(window, "5-prepare")

    if wanted("6-backup-progress") or wanted("6-backup"):
        window, runner, _s = build(app, tmp, "backup", interval_ms=250)
        page = window.pages["backup"]
        wait_until(app, lambda: page.progress._pct == 60.0 and page.banner.isVisible())
        if wanted("6-backup-progress"):
            written.append(save(app, window, "6-backup-progress", dark))
        wait_until(app, lambda: page.result is not None, timeout_s=10)
        if wanted("6-backup"):
            written.append(save(app, window, "6-backup", dark))
        window.close()

    if wanted("7-build"):
        window, _r, _s = build(app, tmp, "build")
        page = window.pages["build"]
        wait_until(app, lambda: page.result is not None)
        emit(window, "7-build")

    if wanted("8-restore") or wanted("8-restore-progress"):
        window, runner, _s = build(app, tmp, "restore", interval_ms=250)
        page = window.pages["restore"]
        if wanted("8-restore"):
            written.append(save(app, window, "8-restore", dark))
        if wanted("8-restore-progress"):
            window.proceed()
            wait_until(app, lambda: page.progress._pct == 75.0 and not page.banner.isVisible(), timeout_s=10)
            written.append(save(app, window, "8-restore-progress", dark))
        window.close()

    if wanted("9-done"):
        window, _r, _s = build(app, tmp, "done")
        emit(window, "9-done")

    if wanted("x-error"):
        window, _r, _s = build(app, tmp, "copy", script={"copy": "android_copy_failed"})
        page = window.pages["copy"]
        wait_until(app, page.error.isVisible)
        emit(window, "x-error")

    return written


def main(argv: list[str]) -> int:
    only = [a for a in argv if not a.startswith("-")]
    app = QApplication.instance() or QApplication(sys.argv[:1])
    load_fonts()
    OUT.mkdir(parents=True, exist_ok=True)
    written: list[Path] = []
    with tempfile.TemporaryDirectory() as tmp:
        for dark in (False, True):
            i18n.set_language("en")
            written += render_all(app, Path(tmp), dark, only)
    for path in written:
        print(path.relative_to(ROOT))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
