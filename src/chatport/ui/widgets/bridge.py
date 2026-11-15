"""The connector between the two phone panels: a 2 px dashed line that only moves while a job runs."""
from __future__ import annotations

from PySide6.QtCore import QElapsedTimer, QPointF, Qt, QTimer
from PySide6.QtGui import QColor, QPainter, QPen
from PySide6.QtWidgets import QSizePolicy, QWidget

from chatport.ui import theme

HEIGHT = 24
WIDTH_PX = 2
DASH = 10
GAP = 8
SPEED_PX_S = 60.0
TICK_MS = 16


class Bridge(QWidget):
    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self._active = False
        self._direction = "right"
        self._into_iphone = False
        self._offset = 0.0
        self.setFixedHeight(HEIGHT)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self._clock = QElapsedTimer()
        self._timer = QTimer(self)
        self._timer.setInterval(TICK_MS)
        self._timer.timeout.connect(self._tick)

    def is_active(self) -> bool:
        return self._active

    def set_active(self, on: bool) -> None:
        self._active = bool(on)
        self._sync_timer()
        self.update()

    def set_direction(self, direction: str) -> None:
        if direction != "right":
            raise ValueError("the bridge only flows from the Android phone to the iPhone")
        self._direction = direction

    def set_into_iphone(self, on: bool) -> None:
        """Restore: the dashes end in a lavender dot, the data is flowing into the iPhone."""
        self._into_iphone = bool(on)
        self.update()

    def showEvent(self, event) -> None:
        super().showEvent(event)
        self._sync_timer()

    def hideEvent(self, event) -> None:
        self._timer.stop()
        super().hideEvent(event)

    def _sync_timer(self) -> None:
        if self._active and self.isVisible():
            if not self._timer.isActive():
                self._clock.start()
                self._timer.start()
        else:
            self._timer.stop()

    def _tick(self) -> None:
        elapsed = self._clock.restart() / 1000.0
        self._offset = (self._offset + SPEED_PX_S * elapsed) % (DASH + GAP)
        self.update()

    def paintEvent(self, _event) -> None:
        p = theme.current()
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        y = self.height() / 2
        color = QColor(p.lime if self._active else p.line)
        pen = QPen(color, WIDTH_PX, Qt.PenStyle.CustomDashLine, Qt.PenCapStyle.FlatCap)
        pen.setDashPattern([DASH / WIDTH_PX, GAP / WIDTH_PX])
        pen.setDashOffset(-self._offset / WIDTH_PX)
        painter.setPen(pen)
        end = self.width() - (10 if self._into_iphone else 0)
        painter.drawLine(QPointF(0, y), QPointF(end, y))
        if self._into_iphone:
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QColor(p.lavender))
            painter.drawEllipse(QPointF(self.width() - 5, y), 5, 5)
        painter.end()
