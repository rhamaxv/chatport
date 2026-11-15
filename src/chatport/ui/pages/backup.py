"""Step 6: a full iPhone backup, then a WhatsApp-only copy the next step can build on."""
from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QPushButton, QVBoxLayout, QWidget

from chatport.i18n import t
from chatport.ui import format as fmt
from chatport.ui.pages.base import Context, Page
from chatport.ui.widgets.banner import Banner
from chatport.ui.widgets.checklist import LiveMark
from chatport.ui.widgets.progress import ProgressBlock


class DoneLine(QWidget):
    """A lime check and one sentence: the job is finished."""

    def __init__(self, text_key: str, parent: QWidget | None = None):
        super().__init__(parent)
        self.text_key = text_key
        self.kw: dict = {}
        row = QHBoxLayout(self)
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(12)
        self.mark = LiveMark()
        self.mark.set_ok(True)
        self.label = QLabel()
        self.label.setWordWrap(True)
        row.addWidget(self.mark, 0, Qt.AlignmentFlag.AlignTop)
        row.addWidget(self.label, 1)

    def show(self, **kw) -> None:
        self.kw = kw
        self.retranslate()

    def retranslate(self) -> None:
        self.label.setText(t(self.text_key, **self.kw))
        self.mark.update()


class BackupPage(Page):
    step = "backup"
    jobs = ("backup",)
    title_key = "backup.title"
    subtitle_key = "backup.subtitle"

    def __init__(self, ctx: Context):
        super().__init__(ctx)
        self.banner = Banner("backup.banner")
        self.banner.setVisible(False)
        self.progress = ProgressBlock(cancellable=True)
        self.progress.cancelled.connect(self.ctx.runner.cancel)
        self.done_card = DoneLine("backup.done")
        self.done_card.setVisible(False)
        self.note = QLabel()
        self.note.setProperty("role", "muted")
        self.note.setWordWrap(True)

        self.reuse_card = QFrame()
        self.reuse_card.setProperty("surface", True)
        reuse_col = QVBoxLayout(self.reuse_card)
        reuse_col.setContentsMargins(24, 20, 24, 20)
        reuse_col.setSpacing(8)
        self.reuse_title = QLabel()
        self.reuse_title.setProperty("role", "heading")
        self.reuse_body = QLabel()
        self.reuse_body.setWordWrap(True)
        buttons = QHBoxLayout()
        buttons.setContentsMargins(0, 8, 0, 0)
        buttons.setSpacing(8)
        self.reuse_button = QPushButton()
        self.reuse_button.setProperty("variant", "primary")
        self.reuse_button.clicked.connect(lambda: self.start_job(reuse=True))
        self.again_button = QPushButton()
        self.again_button.clicked.connect(lambda: self.start_job(reuse=False))
        buttons.addWidget(self.reuse_button)
        buttons.addWidget(self.again_button)
        buttons.addStretch(1)
        reuse_col.addWidget(self.reuse_title)
        reuse_col.addWidget(self.reuse_body)
        reuse_col.addLayout(buttons)
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
