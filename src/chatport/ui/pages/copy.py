"""Step 4: copy the database, contact names and media from the Android phone, then decrypt and summarize."""
from __future__ import annotations

from PySide6.QtWidgets import QHBoxLayout, QLabel, QVBoxLayout

from chatport.i18n import t
from chatport.ui import format as fmt
from chatport.ui.pages.base import Context, Page
from chatport.ui.widgets.cards import Card
from chatport.ui.widgets.progress_card import ProgressCard

STATS = (("chats", "copy.summary.chats"), ("groups", "copy.summary.groups"),
         ("messages", "copy.summary.messages"), ("media", "copy.summary.media"))


class Stat(QVBoxLayout):
    def __init__(self, label_key: str):
        super().__init__()
        self.setSpacing(2)
        self.label_key = label_key
        self.value = QLabel("0")
        self.value.setProperty("role", "stat")
        self.caption = QLabel()
        self.caption.setProperty("role", "muted")
        self.addWidget(self.value)
        self.addWidget(self.caption)

    def retranslate(self) -> None:
        self.caption.setText(t(self.label_key))


class SummaryCard(Card):
    def __init__(self):
        super().__init__(padding=24, spacing=14)
        self.heading = QLabel()
        self.heading.setProperty("role", "heading")
        self.body.addWidget(self.heading)
        row = QHBoxLayout()
        row.setSpacing(28)
        self.stats = {key: Stat(label) for key, label in STATS}
        for stat in self.stats.values():
            row.addLayout(stat)
        row.addStretch(1)
        self.body.addLayout(row)
        self.range = QLabel()
        self.range.setProperty("role", "muted")
        self.body.addWidget(self.range)
        self.data: dict = {}

    def show(self, data: dict) -> None:
        self.data = dict(data)
        self.retranslate()

    def retranslate(self) -> None:
        self.heading.setText(t("copy.summary.title"))
        for key, stat in self.stats.items():
            stat.value.setText(fmt.number(self.data.get(key)))
            stat.retranslate()
        first, last = fmt.date_ms(self.data.get("first_ms")), fmt.date_ms(self.data.get("last_ms"))
        self.range.setText(t("copy.summary.range", first=first, last=last) if first and last else "")


class CopyPage(Page):
    step = "copy"
    jobs = ("copy",)
    title_key = "copy.title"
    subtitle_key = "copy.subtitle"

    def __init__(self, ctx: Context):
        super().__init__(ctx)
        self.progress = ProgressCard(cancellable=True)
        self.progress.cancelled.connect(self.ctx.runner.cancel)
        self.summary = SummaryCard()
        self.body.addWidget(self.progress)
        self.body.addWidget(self.summary)
        self.track(self.progress)
        self.track(self.summary)
        self.result: dict | None = None
        self.retranslate()

    def on_enter(self) -> None:
        saved = self.ctx.state.get(self.step)
        if saved:
            self._finish(saved)
        elif not self.ctx.runner.busy():
            self.start_job()

    def start_job(self) -> None:
        self.clear_error()
        self.result = None
        self.progress.reset()
        self.progress.setVisible(True)
        self.summary.setVisible(False)
        self.busy_changed.emit(True)
        self.continue_changed.emit(False)
        self.ctx.runner.copy()

    def on_event(self, event) -> None:
        if event.kind == "progress":
            self.progress.update_from(event)
        elif event.kind == "done":
            self._finish(event.data)
        elif event.kind == "error":
            self.progress.setVisible(False)
            super().on_event(event)

    def _finish(self, data: dict) -> None:
        self.result = dict(data)
        self.progress.setVisible(False)
        self.summary.show(data)
        self.summary.setVisible(True)
        self.busy_changed.emit(False)
        self.continue_changed.emit(True)

    def can_continue(self) -> bool:
        return self.result is not None

    def stats(self) -> dict:
        keep = ("chats", "groups", "messages", "media", "first_ms", "last_ms", "contacts", "media_bytes")
        return {k: self.result.get(k) for k in keep if self.result and k in self.result}

    def error_fallback_action(self) -> str | None:
        return "retry"
