"""Step 7: merge the Android chats into the WhatsApp copy and explain what came across and what did not."""
from __future__ import annotations

from PySide6.QtWidgets import QHBoxLayout, QLabel, QVBoxLayout

from chatport.i18n import t
from chatport.ui import format as fmt
from chatport.ui.pages.base import Context, Page
from chatport.ui.widgets.cards import Card, IconLabel
from chatport.ui.widgets.progress_card import ProgressCard


def _line(key: str, n: int, **kw) -> str:
    return t(key, n=fmt.number(n), **kw)


def coverage_lines(result: dict) -> tuple[list[str], list[str]]:
    """Plain sentences for the two columns of the coverage card."""
    came = [
        _line("build.messages_added", result.get("messages_added", 0)),
        _line("build.chats_created", result.get("chats_created", 0)),
        _line("build.chats_merged", result.get("chats_merged", 0)),
        _line("build.media_found", result.get("media_found", 0)),
    ]
    missed: list[str] = []
    coverage = result.get("coverage") or {}
    for reason, count in sorted((coverage.get("skipped") or {}).items(), key=lambda kv: -int(kv[1] or 0)):
        if not count:
            continue
        key = f"build.skipped.{reason}"
        text = t(key, n=fmt.number(count))
        missed.append(text if text != key else _line("build.skipped.generic", count, kind=reason.replace("_", " ")))
    for table, count in sorted((coverage.get("unconverted_tables") or {}).items(), key=lambda kv: -int(kv[1] or 0)):
        if not count:
            continue
        key = f"build.table.{table}"
        text = t(key, n=fmt.number(count))
        missed.append(text if text != key else _line("build.table.generic", count, name=table.replace("_", " ")))
    if result.get("media_missing"):
        missed.append(_line("build.media_missing", result["media_missing"]))
    return came, missed


class Column(QVBoxLayout):
    def __init__(self, icon_name: str, color_key: str, title_key: str):
        super().__init__()
        self.setSpacing(8)
        self.title_key = title_key
        head = QHBoxLayout()
        head.setSpacing(10)
        self.icon = IconLabel(icon_name, 20, color_key)
        self.heading = QLabel()
        self.heading.setProperty("role", "heading")
        head.addWidget(self.icon)
        head.addWidget(self.heading, 1)
        self.addLayout(head)
        self.lines = QLabel()
        self.lines.setWordWrap(True)
        self.lines.setProperty("role", "muted")
        self.addWidget(self.lines)
        self.addStretch(1)

    def set_lines(self, lines: list[str], empty_key: str) -> None:
        self.heading.setText(t(self.title_key))
        self.lines.setText("\n".join(lines) if lines else t(empty_key))
        self.icon.refresh()


class CoverageCard(Card):
    def __init__(self):
        super().__init__(padding=24, spacing=12)
        row = QHBoxLayout()
        row.setSpacing(32)
        self.came = Column("check", "accent", "build.coverage.title")
        self.missed = Column("info", "text_muted", "build.not.title")
        row.addLayout(self.came, 1)
        row.addLayout(self.missed, 1)
        self.body.addLayout(row)
        self.result: dict = {}

    def show(self, result: dict) -> None:
        self.result = dict(result)
        self.retranslate()

    def retranslate(self) -> None:
        came, missed = coverage_lines(self.result)
        self.came.set_lines(came, "build.nothing")
        self.missed.set_lines(missed, "build.nothing_missed")


class BuildPage(Page):
    step = "build"
    jobs = ("build",)
    title_key = "build.title"
    subtitle_key = "build.subtitle"

    def __init__(self, ctx: Context):
        super().__init__(ctx)
        self.progress = ProgressCard(cancellable=True)
        self.progress.cancelled.connect(self.ctx.runner.cancel)
        self.coverage = CoverageCard()
        self.coverage.setVisible(False)
        self.body.addWidget(self.progress)
        self.body.addWidget(self.coverage)
        self.track(self.progress)
        self.track(self.coverage)
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
        self.coverage.setVisible(False)
        self.busy_changed.emit(True)
        self.continue_changed.emit(False)
        self.ctx.runner.build(self.ctx.password)

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
        self.coverage.show(data)
        self.coverage.setVisible(True)
        self.busy_changed.emit(False)
        self.continue_changed.emit(True)

    def can_continue(self) -> bool:
        return self.result is not None

    def stats(self) -> dict:
        if not self.result:
            return {}
        keep = ("chats_created", "chats_merged", "messages_added", "media_found", "media_missing", "coverage")
        return {k: self.result[k] for k in keep if k in self.result}

    def error_fallback_action(self) -> str | None:
        return "retry"
