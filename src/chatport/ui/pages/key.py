"""Step 3: the 64-digit end-to-end backup key, checked against a small sample before any long copy."""
from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication, QHBoxLayout, QLabel, QPushButton, QVBoxLayout

from chatport.i18n import t
from chatport.ui.pages.base import Context, Page
from chatport.ui.widgets.cards import Card, Chip
from chatport.ui.widgets.key_grid import KeyGrid
from chatport.ui.widgets.progress_bar import SlimBar


class KeyPage(Page):
    step = "key"
    jobs = ("key",)
    title_key = "key.title"
    subtitle_key = "key.subtitle"

    def __init__(self, ctx: Context):
        super().__init__(ctx)
        self._busy = False
        card = Card(padding=24, spacing=14)
        header = QHBoxLayout()
        self.hint = QLabel()
        self.hint.setProperty("role", "muted")
        self.hint.setWordWrap(True)
        self.paste_button = QPushButton()
        self.paste_button.setProperty("variant", "quiet")
        self.paste_button.clicked.connect(lambda: self.grid.paste(QApplication.clipboard().text()))
        header.addWidget(self.hint, 1)
        header.addWidget(self.paste_button)
        card.body.addLayout(header)
        self.grid = KeyGrid()
        self.grid.changed.connect(self._on_changed)
        card.body.addWidget(self.grid)
        self.checking_bar = SlimBar()
        self.checking_bar.set_value(None)
        self.checking_label = QLabel()
        self.checking_label.setProperty("role", "muted")
        card.body.addWidget(self.checking_bar)
        card.body.addWidget(self.checking_label)
        self._set_checking(False)
        self.body.addWidget(card)

        howto = Card(padding=20, spacing=8)
        row = QHBoxLayout()
        row.setSpacing(16)
        self.howto_icon = Chip("key", 40, "amber")
        row.addWidget(self.howto_icon, 0, Qt.AlignmentFlag.AlignTop)
        text_col = QVBoxLayout()
        text_col.setSpacing(6)
        self.howto_title = QLabel()
        self.howto_title.setProperty("role", "heading")
        self.howto_body = QLabel()
        self.howto_body.setWordWrap(True)
        self.howto_body.setProperty("role", "muted")
        self.howto_path = QLabel()
        self.howto_path.setWordWrap(True)
        self.howto_path.setProperty("role", "mono")
        text_col.addWidget(self.howto_title)
        text_col.addWidget(self.howto_body)
        text_col.addSpacing(4)
        text_col.addWidget(self.howto_path)
        row.addLayout(text_col, 1)
        howto.body.addLayout(row)
        self.body.addWidget(howto)
        self.retranslate()

    def retranslate(self) -> None:
        super().retranslate()
        self.hint.setText(t("key.hint"))
        self.paste_button.setText(t("key.paste"))
        self.checking_label.setText(t("key.checking"))
        self.howto_title.setText(t("key.howto.title"))
        self.howto_body.setText(t("key.howto.body"))
        self.howto_path.setText(t("key.howto.path"))
        self.howto_icon.refresh()

    def on_enter(self) -> None:
        self.grid.set_invalid(False)
        self.clear_error()
        self.grid.boxes[0].setFocus()

    def continue_label_key(self) -> str:
        return "key.continue"

    def can_continue(self) -> bool:
        return self.grid.is_complete() and not self._busy

    def on_continue(self) -> None:
        self.start_job()

    def start_job(self) -> None:
        if not self.grid.is_complete():
            return
        self.clear_error()
        self.grid.set_invalid(False)
        self._set_checking(True)
        self.ctx.runner.check_key(self.grid.text())

    def on_event(self, event) -> None:
        if event.kind == "done":
            self._set_checking(False)
            self.advance.emit()
        elif event.kind == "error":
            self._set_checking(False)
            if event.data.get("code") in ("key_wrong", "key_format"):
                self.grid.set_invalid(True)
            super().on_event(event)

    def _set_checking(self, on: bool) -> None:
        self._busy = on
        self.checking_bar.setVisible(on)
        self.checking_label.setVisible(on)
        self.grid.set_enabled(not on)
        self.busy_changed.emit(on)
        self.continue_changed.emit(self.can_continue())

    def _on_changed(self, _text: str) -> None:
        self.grid.set_invalid(False)
        self.continue_changed.emit(self.can_continue())
