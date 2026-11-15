"""Application entry: logging, fonts, theme, language, the engine wiring, and the window."""
from __future__ import annotations

import locale
import logging
import os
import shutil
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path

from PySide6.QtCore import QLocale, Qt
from PySide6.QtGui import QFontDatabase
from PySide6.QtWidgets import QApplication

from chatport import APP_NAME, __version__
from chatport.core import paths
from chatport.core.state import State
from chatport.ui import theme
from chatport.ui.icons import ASSETS

log = logging.getLogger("chatport")


def setup_logging() -> Path:
    log_path = paths.log_dir() / "chatport.log"
    handler = RotatingFileHandler(log_path, maxBytes=2_000_000, backupCount=3, encoding="utf-8")
    handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s"))
    root = logging.getLogger()
    root.setLevel(logging.INFO)
    root.addHandler(handler)
    logging.getLogger("chatport").info("Chatport %s starting", __version__)
    return log_path


FONT_FILES = ("Inter-Regular.ttf", "Inter-Medium.ttf", "Inter-SemiBold.ttf",
              "BricolageGrotesque-SemiBold.ttf", "BricolageGrotesque-Bold.ttf")


def load_fonts() -> bool:
    """Inter for body text, Bricolage Grotesque for headings. A font that fails to load is skipped silently
    and the stylesheet's fallback family takes over."""
    fonts = ASSETS / "fonts"
    loaded = 0
    for name in FONT_FILES:
        path = fonts / name
        if path.is_file() and QFontDatabase.addApplicationFont(str(path.resolve())) >= 0:
            loaded += 1
        else:
            log.info("font %s not loaded, using a fallback", name)
    return loaded > 0


def pick_language(state: State) -> str:
    saved = getattr(state, "lang", None)
    if saved in ("en", "id"):
        return saved
    forced = os.environ.get("CHATPORT_LANG", "").lower()
    if forced in ("en", "id"):
        return forced
    name = QLocale.system().name() or (locale.getlocale()[0] or "")
    return "id" if name.lower().startswith("id") else "en"


def make_cleanup(work_root: Path):
    """Remove the private copies in the work folder. The full iPhone backup stays unless asked."""

    def cleanup(also_backup: bool) -> None:
        keep = work_root / "ios" / "full"
        for child in list(work_root.iterdir()):
            if child.name == "state.json":
                continue
            if child.name == "ios" and child.is_dir():
                for sub in list(child.iterdir()):
                    if sub == keep and not also_backup:
                        continue
                    shutil.rmtree(sub, ignore_errors=True) if sub.is_dir() else sub.unlink(missing_ok=True)
                if also_backup or not keep.exists():
                    shutil.rmtree(child, ignore_errors=True)
                continue
            shutil.rmtree(child, ignore_errors=True) if child.is_dir() else child.unlink(missing_ok=True)
        log.info("private copies removed (backup kept: %s)", not also_backup)

    return cleanup


def build_fake():
    """CHATPORT_FAKE=1: the scripted runner from tests/, so the UI runs without phones."""
    try:
        from tests.fake_runner import FakeRunner, fake_checks, fake_ready_checks
    except ImportError:
        sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "tests"))
        from fake_runner import FakeRunner, fake_checks, fake_ready_checks

    return FakeRunner(), fake_checks, fake_ready_checks


def build_real(state: State):
    from chatport.core.checks import connect_checks, ready_checks
    from chatport.core.engine import Engine
    from chatport.core.jobs import JobRunner
    from chatport.tools import adb as tools_adb
    from chatport.tools import platform as tools_platform

    def locate_adb() -> str | None:
        """Find adb and point the engine at it, every time: it may have been installed a moment ago."""
        found = tools_adb.find(paths.adb_dir())
        if found:
            tools_adb.use(found)
        return found

    def install_adb(on_progress) -> str:
        installed = tools_adb.download(paths.adb_dir(), on_progress)
        tools_adb.use(installed)
        return installed

    locate_adb()
    runner = JobRunner(Engine(), paths.work_dir(), state, adb_installer=install_adb)
    checks_fn = lambda: connect_checks(Engine(), locate_adb(), paths.work_dir(), tools_platform.check)  # noqa: E731
    ready_fn = lambda: ready_checks(Engine())  # noqa: E731
    return runner, checks_fn, ready_fn


def main() -> int:
    QApplication.setHighDpiScaleFactorRoundingPolicy(Qt.HighDpiScaleFactorRoundingPolicy.PassThrough)
    app = QApplication(sys.argv)
    app.setApplicationName(APP_NAME)
    app.setOrganizationName("Chatport")
    app.setApplicationVersion(__version__)
    log_path = setup_logging()
    load_fonts()
    theme.apply(app, theme.os_prefers_dark())
    state = State(paths.state_file()).load()
    language = pick_language(state)
    fake = os.environ.get("CHATPORT_FAKE") == "1"
    runner, checks_fn, ready_fn = build_fake() if fake else build_real(state)
    from chatport.ui.window import MainWindow

    window = MainWindow(runner, state, checks_fn, language, ready_checks_fn=ready_fn,
                        cleanup=make_cleanup(paths.work_dir()), log_path=log_path)
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
