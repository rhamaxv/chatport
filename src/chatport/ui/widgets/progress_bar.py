"""A slim rounded bar with an accent gradient. Indeterminate shows a highlight sweeping across the track."""
from __future__ import annotations

from PySide6.QtCore import QRectF, Qt, QTimer
from PySide6.QtGui import QColor, QLinearGradient, QPainter, QPainterPath
from PySide6.QtWidgets import QSizePolicy, QWidget

from chatport.ui import theme

HEIGHT = 10
SWEEP_WIDTH = 0.32     # fraction of the track the indeterminate highlight covers
SWEEP_STEP = 0.018     # fraction moved per tick
TICK_MS = 33


class SlimBar(QWidget):
    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self._value: float | None = None
        self._phase = 0.0
        self.setFixedHeight(HEIGHT)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self._timer = QTimer(self)
        self._timer.setInterval(TICK_MS)
        self._timer.timeout.connect(self._tick)

    def value(self) -> float | None:
        return self._value

    def set_value(self, pct: float | None) -> None:
        """0..100, or None for indeterminate."""
        self._value = None if pct is None else max(0.0, min(100.0, float(pct)))
        self._sync_timer()
        self.update()

    def showEvent(self, event) -> None:
        super().showEvent(event)
        self._sync_timer()

    def hideEvent(self, event) -> None:
        self._timer.stop()
        super().hideEvent(event)

    def _sync_timer(self) -> None:
        if self._value is None and self.isVisible():
            if not self._timer.isActive():
                self._timer.start()
        else:
            self._timer.stop()

    def _tick(self) -> None:
        self._phase = (self._phase + SWEEP_STEP) % (1.0 + SWEEP_WIDTH)
        self.update()

    def paintEvent(self, _event) -> None:
        p = theme.current()
        w, h = self.width(), self.height()
        radius = h / 2
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setPen(Qt.PenStyle.NoPen)
        track = QColor(theme.mix(p.surface2, "#FFFFFF", 0.06) if p.dark else p.surface2)
        painter.setBrush(track)
        painter.drawRoundedRect(QRectF(0, 0, w, h), radius, radius)

        clip = QPainterPath()
        clip.addRoundedRect(QRectF(0, 0, w, h), radius, radius)
        painter.setClipPath(clip)
        light = QColor(theme.mix(p.accent, "#FFFFFF", 0.22))
        if self._value is None:
            start = (self._phase - SWEEP_WIDTH) * w
            width = SWEEP_WIDTH * w
            gradient = QLinearGradient(start, 0, start + width, 0)
            faint = QColor(p.accent)
            faint.setAlphaF(0.0)
            gradient.setColorAt(0.0, faint)
            gradient.setColorAt(0.5, QColor(p.accent))
            gradient.setColorAt(1.0, faint)
            painter.setBrush(gradient)
            painter.drawRect(QRectF(start, 0, width, h))
        elif self._value > 0:
            fill = max(h, w * self._value / 100.0)
            gradient = QLinearGradient(0, 0, fill, 0)
            gradient.setColorAt(0.0, light)
            gradient.setColorAt(1.0, QColor(p.accent))
            painter.setBrush(gradient)
            painter.drawRoundedRect(QRectF(0, 0, fill, h), radius, radius)
        painter.end()
