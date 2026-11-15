"""A warning strip: ink text on lime at 30 percent, e.g. "enter the passcode on the iPhone"."""
from __future__ import annotations

from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QWidget

from chatport.i18n import t


class Banner(QFrame):
    def __init__(self, text_key: str, parent: QWidget | None = None):
        super().__init__(parent)
        self.setProperty("warn", True)
        self.text_key = text_key
        row = QHBoxLayout(self)
        row.setContentsMargins(16, 12, 16, 12)
        self.label = QLabel()
        self.label.setWordWrap(True)
        row.addWidget(self.label, 1)
        self.retranslate()

    def retranslate(self) -> None:
        self.label.setText(t(self.text_key))
