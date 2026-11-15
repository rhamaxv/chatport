"""The left rail: nine numbered steps joined by a line that fills with the accent up to the current one."""
from __future__ import annotations

from PySide6.QtCore import QRectF, Qt
from PySide6.QtGui import QColor, QFont, QPainter, QPen, QPixmap
from PySide6.QtWidgets import QWidget

from chatport.core.steps import STEPS
from chatport.i18n import t
from chatport.ui import icons, theme

CIRCLE = 28
ROW = 50
LINE_GAP = 3
TOP = 26
LEFT = 24
BRAND_ICON = 26


class StepRail(QWidget):
    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.setObjectName("rail")
        self.setFixedWidth(theme.RAIL_WIDTH)
        self._current = STEPS[0]
        self._done: set[str] = set()
        self._brand: QPixmap | None = None
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)

    def set_progress(self, current: str, done: set[str]) -> None:
        self._current = current
        self._done = set(done)
        self.update()

    def retranslate(self) -> None:
        self.update()

    def _brand_pixmap(self) -> QPixmap:
        dpr = self.devicePixelRatioF()
        if self._brand is None or self._brand.devicePixelRatio() != dpr:
            source = QPixmap(str(icons.ASSETS / "app-icon.png"))
            px = int(BRAND_ICON * dpr)
            self._brand = source.scaled(px, px, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
            self._brand.setDevicePixelRatio(dpr)
        return self._brand

    def paintEvent(self, event) -> None:
        super().paintEvent(event)
        p = theme.current()
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setRenderHint(QPainter.RenderHint.TextAntialiasing)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)

        brand_icon = self._brand_pixmap()
        if not brand_icon.isNull():
            painter.drawPixmap(LEFT, TOP, brand_icon)
        brand = QFont(self.font())
        brand.setPixelSize(17)
        brand.setWeight(QFont.Weight.DemiBold)
        brand.setLetterSpacing(QFont.SpacingType.AbsoluteSpacing, -0.3)
        painter.setFont(brand)
        painter.setPen(QColor(p.text))
        painter.drawText(LEFT + BRAND_ICON + 10, TOP + 19, t("app.name"))

        label_font = QFont(self.font())
        label_font.setPixelSize(14)
        number_font = QFont(self.font())
        number_font.setPixelSize(12)
        number_font.setWeight(QFont.Weight.DemiBold)

        start_y = TOP + 64
        line_x = LEFT + CIRCLE / 2
        current_index = STEPS.index(self._current) if self._current in STEPS else 0
        accent = QColor(p.accent)
        faint = QColor(p.text_muted)
        faint.setAlphaF(0.28)
        soft = QColor(p.accent)
        soft.setAlphaF(0.14)

        for i, step in enumerate(STEPS):
            cy = start_y + i * ROW + CIRCLE / 2
            done = (step in self._done or i < current_index) and i != current_index
            current = i == current_index
            if i < len(STEPS) - 1:
                # The segment below a step is accent only when the path has been walked past it.
                filled = i < current_index
                painter.setPen(QPen(accent if filled else faint, 2, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
                painter.drawLine(int(line_x), int(cy + CIRCLE / 2 + LINE_GAP), int(line_x),
                                 int(cy + ROW - CIRCLE / 2 - LINE_GAP))
            rect = QRectF(LEFT, cy - CIRCLE / 2, CIRCLE, CIRCLE)
            if done:
                painter.setPen(Qt.PenStyle.NoPen)
                painter.setBrush(accent)
                painter.drawEllipse(rect)
                check = icons.pixmap("check", 16, "#FFFFFF", self.devicePixelRatioF())
                painter.drawPixmap(int(LEFT + 6), int(cy - 8), check)
            elif current:
                painter.setPen(QPen(accent, 2))
                painter.setBrush(soft)
                painter.drawEllipse(rect.adjusted(1, 1, -1, -1))
                painter.setFont(number_font)
                painter.setPen(accent)
                painter.drawText(rect, Qt.AlignmentFlag.AlignCenter, str(i + 1))
            else:
                ring = QColor(p.text_muted)
                ring.setAlphaF(0.45)
                painter.setPen(QPen(ring, 1.5))
                painter.setBrush(Qt.BrushStyle.NoBrush)
                painter.drawEllipse(rect.adjusted(1, 1, -1, -1))
                painter.setFont(number_font)
                painter.setPen(QColor(p.text_muted))
                painter.drawText(rect, Qt.AlignmentFlag.AlignCenter, str(i + 1))
            label_font.setWeight(QFont.Weight.DemiBold if current else QFont.Weight.Normal)
            painter.setFont(label_font)
            painter.setPen(QColor(p.text if current else p.text_muted))
            painter.drawText(LEFT + CIRCLE + 14, int(cy + 5), t(f"step.{step}"))
        painter.end()
