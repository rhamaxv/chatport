"""A chunky stat tile: a big Bricolage number over its label, on a lime or lavender fill."""
from __future__ import annotations

from PySide6.QtCore import QRectF, Qt
from PySide6.QtGui import QColor, QPainter
from PySide6.QtWidgets import QFrame, QLabel, QSizePolicy, QVBoxLayout, QWidget

from chatport.i18n import t
from chatport.ui import theme


class StatTile(QFrame):
    def __init__(self, label_key: str, fill: str = "lime", parent: QWidget | None = None):
        super().__init__(parent)
        self.label_key = label_key
        self._fill = fill
        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 16, 18, 16)
        layout.setSpacing(2)
        self.value = QLabel("0")
        self.value.setProperty("role", "stat")
        self.label = QLabel()
        self.label.setProperty("role", "stat-label")
        self.label.setWordWrap(True)
        layout.addWidget(self.value)
        layout.addWidget(self.label)
        layout.addStretch(1)
        self.setMinimumHeight(92)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        self.retranslate()

    def set_value(self, text: str) -> None:
        self.value.setText(text)

    def retranslate(self) -> None:
        self.label.setText(t(self.label_key))

    def paintEvent(self, _event) -> None:
        p = theme.current()
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor(p.lavender if self._fill == "lavender" else p.lime))
        painter.drawRoundedRect(QRectF(0, 0, self.width(), self.height()), theme.TILE_RADIUS, theme.TILE_RADIUS)
        painter.end()
