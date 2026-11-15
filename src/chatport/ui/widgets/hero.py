"""A page header with an icon: a tinted gradient band (Welcome) or a shadowed card (Done)."""
from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import QHBoxLayout, QLabel, QSizePolicy, QVBoxLayout, QWidget

from chatport.ui import icons
from chatport.ui.widgets.cards import Card, Chip

APP_ICON = 72


class AppIcon(QLabel):
    def __init__(self, size: int = APP_ICON, parent: QWidget | None = None):
        super().__init__(parent)
        self.setFixedSize(size, size)
        source = QPixmap(str(icons.ASSETS / "app-icon.png"))
        dpr = 2.0
        scaled = source.scaled(int(size * dpr), int(size * dpr), Qt.AspectRatioMode.KeepAspectRatio,
                               Qt.TransformationMode.SmoothTransformation)
        scaled.setDevicePixelRatio(dpr)
        self.setPixmap(scaled)
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)


class Hero(Card):
    """`icon` is "app" for the application icon, otherwise an icon name drawn as a big circular chip.

    `card=True` renders as a normal shadowed card; otherwise as a flat accent-tinted band.
    `extra` is a layout under the title for page-specific content such as stat tiles.
    """

    def __init__(self, icon: str, card: bool = False, hue: str = "teal", parent: QWidget | None = None):
        super().__init__(parent, padding=24, spacing=18, nested=not card)
        if not card:
            self.set_tone("hero")
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Maximum)
        row = QHBoxLayout()
        row.setSpacing(22)
        if icon == "app":
            self.icon: QWidget = AppIcon()
        else:
            self.icon = Chip(icon, 64, hue, circle=True)
        row.addWidget(self.icon, 0, Qt.AlignmentFlag.AlignVCenter)
        text = QVBoxLayout()
        text.setSpacing(6)
        self.title = QLabel()
        self.title.setProperty("role", "title")
        self.title.setWordWrap(True)
        self.subtitle = QLabel()
        self.subtitle.setProperty("role", "subtitle")
        self.subtitle.setWordWrap(True)
        text.addWidget(self.title)
        text.addWidget(self.subtitle)
        row.addLayout(text, 1)
        self.body.addLayout(row)
        self.extra = QVBoxLayout()
        self.extra.setSpacing(12)
        self.body.addLayout(self.extra)

    def refresh(self) -> None:
        if isinstance(self.icon, Chip):
            self.icon.refresh()
