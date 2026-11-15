"""What every wizard page shares: title, subtitle, a body of cards, error display and job hooks."""
from __future__ import annotations

import logging
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path

from PySide6.QtCore import QTimer, Signal
from PySide6.QtWidgets import QApplication, QLabel, QMessageBox, QVBoxLayout, QWidget

from chatport.i18n import t
from chatport.ui.widgets.error_card import ErrorCard
from chatport.ui.widgets.hero import Hero

log = logging.getLogger("chatport.ui")

PAGE_PADDING = 32
GAP = 16


@dataclass
class Context:
    """Everything a page may need. The password lives here, in memory only, for the iPhone steps."""

    runner: object
    state: object
    checks_fn: Callable[[], dict] | None = None
    ready_checks_fn: Callable[[], dict] | None = None
    cleanup: Callable[[bool], None] | None = None
    log_path: Path | None = None
    password: str | None = None
    last_connect: dict = field(default_factory=dict)

    def iphone_encrypted(self) -> bool:
        if self.last_connect:
            return bool((self.last_connect.get("iphone") or {}).get("encrypted"))
        saved = self.state.get("connect") or {}
        return bool(saved.get("iphone_encrypted"))


class Page(QWidget):
    step: str = ""
    jobs: tuple[str, ...] = ()
    title_key: str = ""
    subtitle_key: str = ""
    # A hero header instead of the plain title block: "app" for the app icon, or an icon name for a big chip.
    hero: str | None = None
    hero_card: bool = False
    hero_hue: str = "teal"

    continue_changed = Signal(bool)
    busy_changed = Signal(bool)
    advance = Signal()
    request_go = Signal(str)
    notice_changed = Signal(str)

    def __init__(self, ctx: Context, parent: QWidget | None = None):
        super().__init__(parent)
        self.ctx = ctx
        self._translatable: list = []
        outer = QVBoxLayout(self)
        outer.setContentsMargins(PAGE_PADDING, 24, PAGE_PADDING, 24)
        outer.setSpacing(0)
        self.head: Hero | None = None
        if self.hero:
            self.head = Hero(self.hero, card=self.hero_card, hue=self.hero_hue)
            self.title = self.head.title
            self.subtitle = self.head.subtitle
            outer.addWidget(self.head)
        else:
            self.title = QLabel()
            self.title.setProperty("role", "title")
            self.title.setWordWrap(True)
            self.subtitle = QLabel()
            self.subtitle.setProperty("role", "subtitle")
            self.subtitle.setWordWrap(True)
            outer.addWidget(self.title)
            outer.addSpacing(6)
            outer.addWidget(self.subtitle)
        outer.addSpacing(24)
        self.error = ErrorCard()
        self.error.setVisible(False)
        self.error.action.connect(self._on_error_action)
        self.error.copy_log.connect(self.copy_log)
        outer.addWidget(self.error)
        self.body = QVBoxLayout()
        self.body.setSpacing(GAP)
        outer.addLayout(self.body)
        self.notice = QLabel()
        self.notice.setProperty("role", "muted")
        self.notice.setWordWrap(True)
        self.notice.setVisible(False)
        outer.addSpacing(12)
        outer.addWidget(self.notice)
        outer.addStretch(1)
        self._notice_timer = QTimer(self)
        self._notice_timer.setSingleShot(True)
        self._notice_timer.timeout.connect(lambda: self.notice.setVisible(False))

    # ----- hooks pages override -----------------------------------------------------------------

    def on_enter(self) -> None:
        pass

    def on_leave(self) -> None:
        pass

    def on_event(self, event) -> None:
        if event.kind == "error":
            self.show_error(event.data, self.error_fallback_action())

    def can_continue(self) -> bool:
        return True

    def continue_label_key(self) -> str:
        return "common.continue"

    def shows_back(self) -> bool:
        return True

    def start_job(self) -> None:
        pass

    def on_continue(self) -> None:
        self.advance.emit()

    def stats(self) -> dict:
        return {}

    def error_fallback_action(self) -> str | None:
        return None

    # ----- shared behaviour ---------------------------------------------------------------------

    def track(self, widget) -> None:
        """Remember a widget with a retranslate() method so language and theme changes reach it."""
        self._translatable.append(widget)

    def retranslate(self) -> None:
        self.title.setText(t(self.title_key))
        self.subtitle.setText(t(self.subtitle_key))
        self.error.retranslate()
        if self.head is not None:
            self.head.refresh()
        for widget in self._translatable:
            widget.retranslate()

    def show_error(self, data: dict, fallback_action: str | None = None) -> None:
        self.error.show_error(data, fallback_action)
        self.error.setVisible(True)
        self.busy_changed.emit(False)
        self.continue_changed.emit(self.can_continue())

    def clear_error(self) -> None:
        self.error.setVisible(False)

    def say(self, text: str, seconds: float = 4.0) -> None:
        self.notice.setText(text)
        self.notice.setVisible(True)
        self._notice_timer.start(int(seconds * 1000))

    def copy_log(self) -> None:
        text = ""
        path = self.ctx.log_path
        if path is not None:
            try:
                text = Path(path).read_text(encoding="utf-8", errors="replace")[-20000:]
            except OSError:
                text = ""
        QApplication.clipboard().setText(text or t("common.log_empty"))
        self.say(t("common.copied"))

    def _on_error_action(self, kind: str, target: str) -> None:
        if kind == "retry":
            self.clear_error()
            self.start_job()
        elif kind == "back" and target:
            self.clear_error()
            self.request_go.emit(target)
        elif kind == "guide":
            self.show_guide()

    def show_guide(self) -> None:
        hint = ""
        try:
            from chatport.tools import platform as tools_platform

            hint = tools_platform.install_hint()
        except Exception:
            log.debug("install hint unavailable", exc_info=True)
        QMessageBox.information(self, t("guide.title"), hint or t("guide.generic"))

    def password_or_ask(self, wrong: bool = False) -> str | None:
        """Return the remembered backup password, asking if the iPhone encrypts backups."""
        if not self.ctx.iphone_encrypted():
            return None
        if self.ctx.password and not wrong:
            return self.ctx.password
        from chatport.ui.widgets.password_dialog import PasswordDialog

        self.ctx.password = PasswordDialog.ask(self, wrong)
        return self.ctx.password
