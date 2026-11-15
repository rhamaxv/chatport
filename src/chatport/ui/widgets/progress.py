"""Job progress for the middle column: a 6 px lime line, the percent as a big number, the time left as text.

Indeterminate progress shows the track alone; the moving connector between the phones is the only motion.
"""
from __future__ import annotations

from PySide6.QtCore import QRectF, Qt, Signal
from PySide6.QtGui import QColor, QPainter
from PySide6.QtWidgets import QHBoxLayout, QLabel, QPushButton, QSizePolicy, QVBoxLayout, QWidget

from chatport.i18n import t
from chatport.ui import format as fmt
from chatport.ui import theme

LINE_HEIGHT = 6


class ProgressLine(QWidget):
    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self._value: float | None = None
        self.setFixedHeight(LINE_HEIGHT)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

    def value(self) -> float | None:
        return self._value

    def set_value(self, pct: float | None) -> None:
        """0..100, or None for indeterminate (track only)."""
        self._value = None if pct is None else max(0.0, min(100.0, float(pct)))
        self.update()

    def paintEvent(self, _event) -> None:
        p = theme.current()
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setPen(Qt.PenStyle.NoPen)
        w, h = self.width(), self.height()
        painter.setBrush(QColor(p.line))
        painter.drawRoundedRect(QRectF(0, 0, w, h), h / 2, h / 2)
        if self._value:
            painter.setBrush(QColor(p.lime))
            painter.drawRoundedRect(QRectF(0, 0, max(h, w * self._value / 100.0), h), h / 2, h / 2)
        painter.end()


class ProgressBlock(QWidget):
    cancelled = Signal()

    def __init__(self, parent: QWidget | None = None, cancellable: bool = True):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(12)
        top = QHBoxLayout()
        top.setSpacing(16)
        self.phase = QLabel()
        self.phase.setProperty("role", "heading")
        self.phase.setWordWrap(True)
        self.cancel_button = QPushButton()
        self.cancel_button.setVisible(cancellable)
        self.cancel_button.clicked.connect(self._cancel)
        top.addWidget(self.phase, 1, Qt.AlignmentFlag.AlignVCenter)
        top.addWidget(self.cancel_button, 0, Qt.AlignmentFlag.AlignVCenter)
        layout.addLayout(top)
        self.line = ProgressLine()
        layout.addWidget(self.line)
        self.percent = QLabel()
        self.percent.setProperty("role", "percent")
        layout.addWidget(self.percent)
        self.eta = QLabel()
        self.eta.setProperty("role", "muted")
        self.eta.setWordWrap(True)
        layout.addWidget(self.eta)
        self._cancelling = False
        self.reset()
        self.retranslate()

    def reset(self) -> None:
        self._cancelling = False
        self._phase_name = None
        self._pct = None
        self._eta = None
        self._done_bytes = None
        self._total_bytes = None
        self.cancel_button.setEnabled(True)
        self._render()

    def update_from(self, event) -> None:
        self._phase_name = event.phase
        self._pct = event.pct
        self._eta = event.eta_s
        self._done_bytes = event.data.get("done_bytes")
        self._total_bytes = event.data.get("total_bytes")
        self._render()

    def finish(self) -> None:
        self._pct = 100
        self._eta = None
        self.cancel_button.setEnabled(False)
        self._render()

    def _cancel(self) -> None:
        self._cancelling = True
        self.cancel_button.setEnabled(False)
        self._render()
        self.cancelled.emit()

    def retranslate(self) -> None:
        self._render()

    def _render(self) -> None:
        self.phase.setText(fmt.phase(self._phase_name))
        self.line.set_value(self._pct)
        self.percent.setText(t("progress.percent", pct=int(self._pct)) if self._pct is not None else t("progress.working"))
        parts = []
        if self._eta is not None and self._pct is not None and self._pct < 100:
            parts.append(t("progress.eta", eta=fmt.duration(self._eta)))
        if self._done_bytes is not None and self._total_bytes:
            parts.append(t("progress.bytes", done=fmt.bytes_text(self._done_bytes), total=fmt.bytes_text(self._total_bytes)))
        self.eta.setText(", ".join(parts))
        self.eta.setVisible(bool(parts))
        self.cancel_button.setText(t("progress.cancelling") if self._cancelling else t("progress.cancel"))
