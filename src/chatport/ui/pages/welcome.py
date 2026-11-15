"""Step 1: the bridge diagram, three plain sentences, one button."""
from __future__ import annotations

from PySide6.QtCore import QRectF, Qt
from PySide6.QtGui import QColor, QPainter
from PySide6.QtWidgets import QHBoxLayout, QLabel, QWidget

from chatport.i18n import t
from chatport.ui import icons, theme
from chatport.ui.pages.base import Context, Page
from chatport.ui.widgets.bridge import Bridge

GLYPH = 72
PARAGRAPHS = (("welcome.what.title", "welcome.what.body"), ("welcome.safe.title", "welcome.safe.body"),
              ("welcome.need.title", "welcome.need.body"))


class PhoneGlyph(QWidget):
    """A phone outline on a lime (Android) or lavender (iPhone) square: the two ends of the bridge."""

    def __init__(self, side: str, parent: QWidget | None = None):
        super().__init__(parent)
        self.side = side
        self.setFixedSize(GLYPH, GLYPH)

    def paintEvent(self, _event) -> None:
        p = theme.current()
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor(p.lavender if self.side == "iphone" else p.lime))
        painter.drawRoundedRect(QRectF(0, 0, GLYPH, GLYPH), theme.PANEL_RADIUS, theme.PANEL_RADIUS)
        name = "phone-iphone" if self.side == "iphone" else "phone-android"
        painter.drawPixmap((GLYPH - 36) // 2, (GLYPH - 36) // 2, icons.pixmap(name, 36, p.on_accent, self.devicePixelRatioF()))
        painter.end()


class WelcomePage(Page):
    step = "welcome"
    title_key = "welcome.title"
    subtitle_key = "welcome.subtitle"

    def __init__(self, ctx: Context):
        super().__init__(ctx)
        diagram = QHBoxLayout()
        diagram.setContentsMargins(0, 8, 0, 8)
        diagram.setSpacing(0)
        self.android_glyph = PhoneGlyph("android")
        self.iphone_glyph = PhoneGlyph("iphone")
        self.bridge = Bridge()
        diagram.addWidget(self.android_glyph, 0, Qt.AlignmentFlag.AlignVCenter)
        diagram.addWidget(self.bridge, 1, Qt.AlignmentFlag.AlignVCenter)
        diagram.addWidget(self.iphone_glyph, 0, Qt.AlignmentFlag.AlignVCenter)
        self.body.addLayout(diagram)
        self.body.addSpacing(8)
        self.paragraphs: list[QLabel] = []
        for _lead, _text in PARAGRAPHS:
            label = QLabel()
            label.setWordWrap(True)
            label.setProperty("role", "lead")
            label.setTextFormat(Qt.TextFormat.RichText)
            self.body.addWidget(label)
            self.paragraphs.append(label)
        self.privacy = QLabel()
        self.privacy.setProperty("role", "muted")
        self.privacy.setWordWrap(True)
        self.body.addWidget(self.privacy)
        self.retranslate()

    def retranslate(self) -> None:
        super().retranslate()
        for label, (lead, text) in zip(self.paragraphs, PARAGRAPHS):
            label.setText(f"<b>{t(lead)}.</b> {t(text)}")
        self.privacy.setText(t("welcome.privacy"))

    def continue_label_key(self) -> str:
        return "welcome.cta"

    def shows_back(self) -> bool:
        return False
