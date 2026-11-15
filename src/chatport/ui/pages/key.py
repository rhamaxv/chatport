"""Step 3: the 64-digit end-to-end backup key, checked against a small sample before any long copy."""
from __future__ import annotations

from PySide6.QtWidgets import QApplication, QHBoxLayout, QLabel, QPushButton

from chatport.i18n import t
from chatport.ui.pages.base import Context, Page
from chatport.ui.widgets.key_grid import KeyGrid


class KeyPage(Page):
    step = "key"
    jobs = ("key",)
    title_key = "key.title"
    subtitle_key = "key.subtitle"

    def __init__(self, ctx: Context):
        super().__init__(ctx)
        self._busy = False
        header = QHBoxLayout()
        self.hint = QLabel()
        self.hint.setProperty("role", "muted")
        self.hint.setWordWrap(True)
        self.paste_button = QPushButton()
        self.paste_button.clicked.connect(lambda: self.grid.paste(QApplication.clipboard().text()))
        header.addWidget(self.hint, 1)
        header.addWidget(self.paste_button)
        self.body.addLayout(header)
        self.grid = KeyGrid()
        self.grid.changed.connect(self._on_changed)
        self.body.addWidget(self.grid)
        self.checking_label = QLabel()
        self.checking_label.setProperty("role", "muted")
        self.body.addWidget(self.checking_label)
        self._set_checking(False)

        self.body.addSpacing(8)
        self.howto_title = QLabel()
        self.howto_title.setProperty("role", "heading")
        self.howto_body = QLabel()
        self.howto_body.setWordWrap(True)
        self.howto_body.setProperty("role", "muted")
        self.howto_path = QLabel()
        self.howto_path.setWordWrap(True)
        self.body.addWidget(self.howto_title)
        self.body.addWidget(self.howto_body)
        self.body.addWidget(self.howto_path)
        self.retranslate()

    def retranslate(self) -> None:
        super().retranslate()
        self.hint.setText(t("key.hint"))
        self.paste_button.setText(t("key.paste"))
        self.checking_label.setText(t("key.checking"))
        self.howto_title.setText(t("key.howto.title"))
        self.howto_body.setText(t("key.howto.body"))
        self.howto_path.setText(t("key.howto.path"))

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
        self.checking_label.setVisible(on)
        self.grid.set_enabled(not on)
        self.busy_changed.emit(on)
        self.continue_changed.emit(self.can_continue())

    def _on_changed(self, _text: str) -> None:
        self.grid.set_invalid(False)
        self.continue_changed.emit(self.can_continue())
