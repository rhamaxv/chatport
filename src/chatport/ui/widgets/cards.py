"""Card surfaces: a plain Card and a StatusCard with icon, title, status line and a colored dot."""
from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QPainter
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QSizePolicy, QVBoxLayout, QWidget

from chatport.ui import icons, theme

TONES = {"green": "success", "amber": "warning", "red": "danger", "gray": "text_muted"}


class Card(QFrame):
    def __init__(self, parent: QWidget | None = None, padding: int = 20, spacing: int = 10):
        super().__init__(parent)
        self.setProperty("card", True)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Maximum)
        self.body = QVBoxLayout(self)
        self.body.setContentsMargins(padding, padding, padding, padding)
        self.body.setSpacing(spacing)

    def set_tone(self, tone: str | None) -> None:
        self.setProperty("tone", tone or "")
        theme.repolish(self)


class Dot(QWidget):
    """A small filled circle in a semantic color."""

    def __init__(self, color_key: str = "text_muted", size: int = 10, parent: QWidget | None = None):
        super().__init__(parent)
        self._key = color_key
        self._size = size
        self.setFixedSize(size, size)

    def set_color(self, color_key: str) -> None:
        self._key = color_key
        self.update()

    def paintEvent(self, _event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor(getattr(theme.current(), self._key)))
        painter.drawEllipse(0, 0, self._size, self._size)
        painter.end()


class IconLabel(QLabel):
    def __init__(self, name: str, size: int = 24, color_key: str = "text", parent: QWidget | None = None):
        super().__init__(parent)
        self._name, self._size, self._key = name, size, color_key
        self.setFixedSize(size, size)
        self.refresh()

    def set_icon(self, name: str, color_key: str | None = None) -> None:
        self._name = name
        if color_key:
            self._key = color_key
        self.refresh()

    def refresh(self) -> None:
        color = getattr(theme.current(), self._key)
        dpr = self.devicePixelRatioF() if self.windowHandle() else 2.0
        self.setPixmap(icons.pixmap(self._name, self._size, color, dpr))


class StatusCard(Card):
    """Icon on the left, a title and a one line status underneath, a colored dot on the right."""

    def __init__(self, icon_name: str, parent: QWidget | None = None):
        super().__init__(parent, padding=18, spacing=0)
        row = QHBoxLayout()
        row.setSpacing(14)
        self.icon = IconLabel(icon_name, 28, "text_muted")
        row.addWidget(self.icon, 0, Qt.AlignmentFlag.AlignTop)
        text = QVBoxLayout()
        text.setSpacing(4)
        self.title = QLabel()
        self.title.setProperty("role", "heading")
        self.status = QLabel()
        self.status.setProperty("role", "muted")
        self.status.setWordWrap(True)
        text.addWidget(self.title)
        text.addWidget(self.status)
        row.addLayout(text, 1)
        self.dot = Dot("text_muted", 10)
        row.addWidget(self.dot, 0, Qt.AlignmentFlag.AlignTop)
        self.body.addLayout(row)
        self.extra = QVBoxLayout()
        self.extra.setContentsMargins(42, 0, 0, 0)
        self.extra.setSpacing(8)
        self.body.addLayout(self.extra)

    def set_state(self, title: str, status: str, tone: str = "gray") -> None:
        self.title.setText(title)
        self.status.setText(status)
        self.dot.set_color(TONES.get(tone, "text_muted"))
        self.icon.set_icon(self.icon._name, "accent" if tone == "green" else "text_muted")
