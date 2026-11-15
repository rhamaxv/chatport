"""Step 8: confirm, then restore the rebuilt WhatsApp data to the iPhone. Cannot be cancelled."""
from __future__ import annotations

from PySide6.QtWidgets import QHBoxLayout, QLabel, QVBoxLayout

from chatport.i18n import t
from chatport.ui.pages.base import Context, Page
from chatport.ui.widgets.banner import Banner
from chatport.ui.widgets.cards import Card, Chip
from chatport.ui.widgets.progress_card import ProgressCard

EFFECTS = ("restore.effect.restart", "restore.effect.layout", "restore.effect.apps", "restore.effect.undo")


class ConfirmCard(Card):
    def __init__(self):
        super().__init__(padding=24, spacing=12)
        head = QHBoxLayout()
        head.setSpacing(14)
        self.icon = Chip("info", 36, "blue")
        self.heading = QLabel()
        self.heading.setProperty("role", "heading")
        head.addWidget(self.icon)
        head.addWidget(self.heading, 1)
        self.body.addLayout(head)
        self.intro = QLabel()
        self.intro.setWordWrap(True)
        self.body.addWidget(self.intro)
        self.points = QLabel()
        self.points.setWordWrap(True)
        self.points.setProperty("role", "muted")
        self.body.addWidget(self.points)
        self.body.setContentsMargins(24, 22, 24, 22)

    def retranslate(self) -> None:
        self.heading.setText(t("restore.confirm.title"))
        self.intro.setText(t("restore.confirm.body"))
        self.points.setText("\n".join("\u2022  " + t(key) for key in EFFECTS))
        self.icon.refresh()


class RestorePage(Page):
    step = "restore"
    jobs = ("restore",)
    title_key = "restore.title"
    subtitle_key = "restore.subtitle"

    def __init__(self, ctx: Context):
        super().__init__(ctx)
        self._running = False
        self.confirm = ConfirmCard()
        self.banner = Banner("lock", "backup.banner")
        self.banner.setVisible(False)
        self.progress = ProgressCard(cancellable=False)
        self.progress.setVisible(False)
        self.running_note = QLabel()
        self.running_note.setProperty("role", "muted")
        self.running_note.setWordWrap(True)
        self.running_note.setVisible(False)
        for widget in (self.confirm, self.banner, self.progress, self.running_note):
            self.body.addWidget(widget)
        for widget in (self.confirm, self.banner, self.progress):
            self.track(widget)
        self.retranslate()

    def retranslate(self) -> None:
        super().retranslate()
        self.running_note.setText(t("restore.running"))

    def continue_label_key(self) -> str:
        return "restore.continue"

    def can_continue(self) -> bool:
        return not self._running

    def on_enter(self) -> None:
        self._set_running(False)
        self.clear_error()

    def on_continue(self) -> None:
        self.start_job()

    def start_job(self) -> None:
        self.clear_error()
        self.progress.reset()
        self._set_running(True)
        self.ctx.runner.restore(self.ctx.password)

    def on_event(self, event) -> None:
        if event.kind == "progress":
            self.progress.update_from(event)
        elif event.kind == "need":
            self.banner.setVisible(True)
        elif event.kind == "clear":
            self.banner.setVisible(False)
        elif event.kind == "done":
            self.progress.finish()
            self._set_running(False)
            self.advance.emit()
        elif event.kind == "error":
            self._set_running(False)
            super().on_event(event)

    def _set_running(self, on: bool) -> None:
        self._running = on
        self.confirm.setVisible(not on)
        self.progress.setVisible(on)
        self.running_note.setVisible(on)
        if not on:
            self.banner.setVisible(False)
        self.busy_changed.emit(on)
        self.continue_changed.emit(self.can_continue())

    def error_fallback_action(self) -> str | None:
        return "retry"
