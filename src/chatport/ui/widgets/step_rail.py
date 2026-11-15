"""The left rail: nine steps as circles joined by a thin line. Filled = done, ring = current, dim = ahead."""
from __future__ import annotations

from PySide6.QtCore import QRectF, Qt
from PySide6.QtGui import QColor, QFont, QPainter, QPen
from PySide6.QtWidgets import QWidget

from chatport.core.steps import STEPS
from chatport.i18n import t
from chatport.ui import icons, theme

CIRCLE = 22
ROW = 46
TOP = 28
LEFT = 24


class StepRail(QWidget):
    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.setObjectName("rail")
        self.setFixedWidth(theme.RAIL_WIDTH)
        self._current = STEPS[0]
        self._done: set[str] = set()
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)

    def set_progress(self, current: str, done: set[str]) -> None:
        self._current = current
        self._done = set(done)
        self.update()

    def retranslate(self) -> None:
        self.update()

    def paintEvent(self, event) -> None:
        super().paintEvent(event)
        p = theme.current()
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setRenderHint(QPainter.RenderHint.TextAntialiasing)

        brand = QFont(self.font())
        brand.setPixelSize(18)
        brand.setWeight(QFont.Weight.DemiBold)
        painter.setFont(brand)
        painter.setPen(QColor(p.text))
        painter.drawText(LEFT, TOP + 18, t("app.name"))

        label_font = QFont(self.font())
        label_font.setPixelSize(15)
        start_y = TOP + 64
        line_x = LEFT + CIRCLE / 2
        current_index = STEPS.index(self._current) if self._current in STEPS else 0
        for i, step in enumerate(STEPS):
            cy = start_y + i * ROW + CIRCLE / 2
            done = step in self._done or i < current_index
            current = step == self._current
            if i < len(STEPS) - 1:
                next_done = STEPS[i + 1] in self._done or (i + 1) < current_index or current
                faint = QColor(p.text_muted)
                faint.setAlpha(70)
                pen = QPen(QColor(p.accent) if done and next_done else faint, 2)
                painter.setPen(pen)
                painter.drawLine(int(line_x), int(cy + CIRCLE / 2 + 3), int(line_x), int(cy + ROW - CIRCLE / 2 - 3))
            rect = QRectF(LEFT, cy - CIRCLE / 2, CIRCLE, CIRCLE)
            if done and not current:
                painter.setPen(Qt.PenStyle.NoPen)
                painter.setBrush(QColor(p.accent))
                painter.drawEllipse(rect)
                check = icons.pixmap("check", 14, p.accent_text, self.devicePixelRatioF())
                painter.drawPixmap(int(LEFT + 4), int(cy - 7), check)
            elif current:
                painter.setPen(QPen(QColor(p.accent), 2))
                painter.setBrush(QColor(p.rail))
                painter.drawEllipse(rect.adjusted(1, 1, -1, -1))
                painter.setPen(Qt.PenStyle.NoPen)
                painter.setBrush(QColor(p.accent))
                painter.drawEllipse(rect.adjusted(7, 7, -7, -7))
            else:
                ring = QColor(p.text_muted)
                ring.setAlpha(110)
                painter.setPen(QPen(ring, 1.5))
                painter.setBrush(Qt.BrushStyle.NoBrush)
                painter.drawEllipse(rect.adjusted(1, 1, -1, -1))
            painter.setFont(label_font)
            if current:
                label_font.setWeight(QFont.Weight.DemiBold)
                painter.setFont(label_font)
                painter.setPen(QColor(p.text))
            else:
                label_font.setWeight(QFont.Weight.Normal)
                painter.setFont(label_font)
                painter.setPen(QColor(p.text if done else p.text_muted))
            painter.drawText(LEFT + CIRCLE + 14, int(cy + 5), t(f"step.{step}"))
        painter.end()
