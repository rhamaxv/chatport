"""The pill stepper across the top: done steps collapse to a check, the current step is the one lime pill
with its name, upcoming steps are numbered dots."""
from __future__ import annotations

from PySide6.QtCore import QRectF, QSize, Qt
from PySide6.QtGui import QColor, QFont, QFontMetrics, QPainter, QPen
from PySide6.QtWidgets import QSizePolicy, QWidget

from chatport.core.steps import STEPS
from chatport.i18n import t
from chatport.ui import icons, theme

DOT = 24
PILL_H = 28
PILL_PAD = 12
GAP = 8


class Stepper(QWidget):
    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self._current = STEPS[0]
        self._done: set[str] = set()
        self.setFixedHeight(PILL_H + 4)
        self.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        self.retranslate()

    def current(self) -> str:
        return self._current

    def set_progress(self, current: str, done: set[str]) -> None:
        self._current = current if current in STEPS else STEPS[0]
        self._done = set(done)
        self.retranslate()

    def retranslate(self) -> None:
        index = STEPS.index(self._current)
        self.setToolTip(t("stepper.step_n", n=index + 1, total=len(STEPS), name=t(f"step.{self._current}")))
        self.setAccessibleName(self.toolTip())
        self.updateGeometry()
        self.update()

    def _label_font(self) -> QFont:
        font = QFont(self.font())
        font.setPixelSize(13)
        font.setWeight(QFont.Weight.DemiBold)
        return font

    def _pill_width(self) -> int:
        return QFontMetrics(self._label_font()).horizontalAdvance(t(f"step.{self._current}")) + 2 * PILL_PAD

    def sizeHint(self) -> QSize:
        width = (len(STEPS) - 1) * DOT + self._pill_width() + (len(STEPS) - 1) * GAP
        return QSize(width, PILL_H + 4)

    def minimumSizeHint(self) -> QSize:
        return self.sizeHint()

    def paintEvent(self, _event) -> None:
        p = theme.current()
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setRenderHint(QPainter.RenderHint.TextAntialiasing)
        number_font = QFont(self.font())
        number_font.setPixelSize(12)
        number_font.setWeight(QFont.Weight.DemiBold)
        current_index = STEPS.index(self._current)
        x = 0.0
        cy = self.height() / 2
        for i, step in enumerate(STEPS):
            if i == current_index:
                width = self._pill_width()
                rect = QRectF(x, cy - PILL_H / 2, width, PILL_H)
                painter.setPen(Qt.PenStyle.NoPen)
                painter.setBrush(QColor(p.lime))
                painter.drawRoundedRect(rect, PILL_H / 2, PILL_H / 2)
                painter.setFont(self._label_font())
                painter.setPen(QColor(p.on_accent))
                painter.drawText(rect, Qt.AlignmentFlag.AlignCenter, t(f"step.{step}"))
                x += width + GAP
                continue
            rect = QRectF(x, cy - DOT / 2, DOT, DOT)
            done = step in self._done or i < current_index
            if done:
                painter.setPen(QPen(QColor(p.text), 1))
                painter.setBrush(QColor(p.panel))
                painter.drawEllipse(rect.adjusted(0.5, 0.5, -0.5, -0.5))
                check = icons.pixmap("check", 14, p.text, self.devicePixelRatioF())
                painter.drawPixmap(int(x + 5), int(cy - 7), check)
            else:
                painter.setPen(QPen(QColor(p.line_strong()), 1))
                painter.setBrush(Qt.BrushStyle.NoBrush)
                painter.drawEllipse(rect.adjusted(0.5, 0.5, -0.5, -0.5))
                painter.setFont(number_font)
                painter.setPen(QColor(p.text_muted))
                painter.drawText(rect, Qt.AlignmentFlag.AlignCenter, str(i + 1))
            x += DOT + GAP
        painter.end()
