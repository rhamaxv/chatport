"""A soft accent strip with an icon chip and one sentence, e.g. "enter the passcode on the iPhone"."""
from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QHBoxLayout, QLabel, QWidget

from chatport.i18n import t
from chatport.ui.widgets.cards import Card, Chip


class Banner(Card):
    def __init__(self, icon_name: str, text_key: str, parent: QWidget | None = None, hue: str = "teal"):
        super().__init__(parent, padding=14, spacing=0, nested=True)
        self.set_tone("accent")
        self.text_key = text_key
        row = QHBoxLayout()
        row.setSpacing(12)
        self.icon = Chip(icon_name, 32, hue)
        row.addWidget(self.icon, 0, Qt.AlignmentFlag.AlignVCenter)
        self.label = QLabel()
        self.label.setWordWrap(True)
        row.addWidget(self.label, 1)
        self.body.addLayout(row)
        self.retranslate()

    def retranslate(self) -> None:
        self.label.setText(t(self.text_key))
        self.icon.refresh()
