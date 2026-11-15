"""Step 6: a full iPhone backup, then a WhatsApp-only copy the next step can build on."""
from __future__ import annotations

from PySide6.QtWidgets import QHBoxLayout, QLabel, QPushButton

from chatport.i18n import t
from chatport.ui import format as fmt
from chatport.ui.pages.base import Context, Page
from chatport.ui.widgets.banner import Banner
from chatport.ui.widgets.cards import Card, IconLabel
from chatport.ui.widgets.progress_card import ProgressCard


class DoneCard(Card):
    def __init__(self, text_key: str):
        super().__init__(padding=20, spacing=0)
        self.text_key = text_key
        self.kw: dict = {}
        row = QHBoxLayout()
        row.setSpacing(14)
        self.icon = IconLabel("check", 24, "accent")
        self.label = QLabel()
        self.label.setWordWrap(True)
        row.addWidget(self.icon)
        row.addWidget(self.label, 1)
        self.body.addLayout(row)

    def show(self, **kw) -> None:
        self.kw = kw
        self.retranslate()

    def retranslate(self) -> None:
        self.label.setText(t(self.text_key, **self.kw))
        self.icon.refresh()


class BackupPage(Page):
    step = "backup"
    jobs = ("backup",)
    title_key = "backup.title"
    subtitle_key = "backup.subtitle"

    def __init__(self, ctx: Context):
        super().__init__(ctx)
        self.banner = Banner("lock", "backup.banner")
        self.banner.setVisible(False)
        self.progress = ProgressCard(cancellable=True)
        self.progress.cancelled.connect(self.ctx.runner.cancel)
        self.done_card = DoneCard("backup.done")
        self.done_card.setVisible(False)
        self.note = QLabel()
        self.note.setProperty("role", "muted")
        self.note.setWordWrap(True)
        self.reuse_card = Card(padding=20, spacing=10)
        self.reuse_title = QLabel()
        self.reuse_title.setProperty("role", "heading")
        self.reuse_body = QLabel()
        self.reuse_body.setWordWrap(True)
        self.reuse_body.setProperty("role", "muted")
        buttons = QHBoxLayout()
        self.reuse_button = QPushButton()
        self.reuse_button.setProperty("variant", "primary")
        self.reuse_button.clicked.connect(lambda: self.start_job(reuse=True))
        self.again_button = QPushButton()
        self.again_button.setProperty("variant", "quiet")
        self.again_button.clicked.connect(lambda: self.start_job(reuse=False))
        buttons.addWidget(self.reuse_button)
        buttons.addWidget(self.again_button)
        buttons.addStretch(1)
        self.reuse_card.body.addWidget(self.reuse_title)
        self.reuse_card.body.addWidget(self.reuse_body)
        self.reuse_card.body.addLayout(buttons)
        self.reuse_card.setVisible(False)
        self._reuse_age: float | None = None
        for widget in (self.reuse_card, self.banner, self.progress, self.done_card, self.note):
            self.body.addWidget(widget)
        for widget in (self.banner, self.progress, self.done_card):
            self.track(widget)
        self.result: dict | None = None
        self.retranslate()

    def retranslate(self) -> None:
        super().retranslate()
        self.note.setText(t("backup.note"))
        self.reuse_title.setText(t("backup.reuse.title"))
        self.reuse_body.setText(t("backup.reuse.body", age=fmt.age(self._reuse_age)))
        self.reuse_button.setText(t("backup.reuse.use"))
        self.again_button.setText(t("backup.reuse.again"))

    def on_enter(self) -> None:
        saved = self.ctx.state.get(self.step)
        if saved:
            self._finish(saved)
        elif not self.ctx.runner.busy():
            udid = ((self.ctx.last_connect or {}).get("iphone") or {}).get("udid")
            self._reuse_age = self.ctx.runner.existing_backup_age(udid)
            if self._reuse_age is None:
                self.start_job()
            else:  # an earlier attempt left a full backup: offer to skip the slow part
                self.progress.setVisible(False)
                self.reuse_card.setVisible(True)
                self.retranslate()

    def start_job(self, reuse: bool = False) -> None:
        self.reuse_card.setVisible(False)
        self.clear_error()
        password = self.password_or_ask()
        if self.ctx.iphone_encrypted() and not password:
            self.show_error({"code": "password_needed"}, "retry")
            self.progress.setVisible(False)
            return
        self.result = None
        self.banner.setVisible(False)
        self.progress.reset()
        self.progress.setVisible(True)
        self.done_card.setVisible(False)
        self.busy_changed.emit(True)
        self.continue_changed.emit(False)
        self.ctx.runner.backup(password, reuse)

    def on_event(self, event) -> None:
        if event.kind == "progress":
            self.progress.update_from(event)
        elif event.kind == "need":
            self.banner.setVisible(True)
        elif event.kind == "clear":
            self.banner.setVisible(False)
        elif event.kind == "done":
            self._finish(event.data)
        elif event.kind == "error":
            self.banner.setVisible(False)
            self.progress.setVisible(False)
            if event.data.get("code") in ("password_wrong", "password_needed"):
                self.ctx.password = None
            super().on_event(event)

    def _finish(self, data: dict) -> None:
        self.result = dict(data)
        self.banner.setVisible(False)
        self.progress.setVisible(False)
        self.done_card.show(n=fmt.number(data.get("entries")))
        self.done_card.setVisible(True)
        self.busy_changed.emit(False)
        self.continue_changed.emit(True)

    def can_continue(self) -> bool:
        return self.result is not None

    def stats(self) -> dict:
        return {k: self.result.get(k) for k in ("entries", "encrypted", "used_bytes") if self.result and k in self.result}

    def error_fallback_action(self) -> str | None:
        return "retry"
