"""One tall device card: the OS name and a state word in the header, up to three facts, a status sentence.

The iPhone header is lavender; the Android header turns lime when that phone is ready or done. A panel
dims when the step does not touch its phone, and collapses to a slim strip in a narrow window.
"""
from __future__ import annotations

from PySide6.QtCore import QRectF, Qt
from PySide6.QtGui import QColor, QPainter, QPainterPath, QPen
from PySide6.QtWidgets import QFrame, QGridLayout, QLabel, QSizePolicy, QVBoxLayout, QWidget

from chatport.i18n import t
from chatport.ui import theme

STATES = ("ready", "waiting", "needs_you", "idle", "moved", "received")
HEADER_H = 64
COMPACT_WIDTH = 120
LIME_STATES = ("ready", "moved")


class PhonePanel(QFrame):
    def __init__(self, side: str, parent: QWidget | None = None):
        super().__init__(parent)
        self.side = side  # "android" or "iphone"
        self._state = "idle"
        self._dimmed = False
        self._compact = False
        self._facts: list[str] = []
        self._status = ""
        self.setFixedWidth(theme.PANEL_WIDTH)
        self.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Expanding)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        self.header = QWidget()
        self.header.setFixedHeight(HEADER_H)
        self.header_grid = QGridLayout(self.header)
        self.header_grid.setContentsMargins(20, 0, 20, 0)
        self.header_grid.setHorizontalSpacing(8)
        self.header_grid.setVerticalSpacing(0)
        self.name = QLabel()
        self.name.setProperty("role", "heading")
        self.state = QLabel()
        self.state.setProperty("role", "state")
        self.header_grid.addWidget(self.name, 0, 0, Qt.AlignmentFlag.AlignVCenter)
        self.header_grid.addWidget(self.state, 0, 1, Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignRight)
        self.header_grid.setColumnStretch(0, 1)
        layout.addWidget(self.header)

        body = QWidget()
        self.body = QVBoxLayout(body)
        self.body.setContentsMargins(20, 20, 20, 20)
        self.body.setSpacing(10)
        self.facts = [QLabel() for _ in range(3)]
        for fact in self.facts:
            fact.setWordWrap(True)
            fact.setVisible(False)
            self.body.addWidget(fact)
        self.body.addStretch(1)
        self.status = QLabel()
        self.status.setProperty("role", "muted")
        self.status.setWordWrap(True)
        self.body.addWidget(self.status)
        layout.addWidget(body, 1)
        self.retranslate()

    # ----- state --------------------------------------------------------------------------------

    def set_state(self, state: str, facts: list[str] | None = None, status: str = "") -> None:
        self._state = state if state in STATES else "idle"
        self._facts = [f for f in (facts or []) if f][:3]
        self._status = status
        self.retranslate()

    def set_dimmed(self, dimmed: bool) -> None:
        if self._dimmed != bool(dimmed):
            self._dimmed = bool(dimmed)
            self.retranslate()

    def set_compact(self, compact: bool) -> None:
        if self._compact == bool(compact):
            return
        self._compact = bool(compact)
        self.header_grid.removeWidget(self.state)
        if self._compact:
            self.header_grid.addWidget(self.state, 1, 0, Qt.AlignmentFlag.AlignLeft)
            self.header_grid.setContentsMargins(16, 10, 16, 10)
            self.setFixedWidth(COMPACT_WIDTH)
        else:
            self.header_grid.addWidget(self.state, 0, 1, Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignRight)
            self.header_grid.setContentsMargins(20, 0, 20, 0)
            self.setFixedWidth(theme.PANEL_WIDTH)
        self.retranslate()

    def state_name(self) -> str:
        return self._state

    # ----- colors -------------------------------------------------------------------------------

    def _header_fill(self) -> str:
        p = theme.current()
        if self.side == "iphone":
            fill = p.lavender
        elif self._state in LIME_STATES:
            fill = p.lime
        else:
            return p.panel
        return theme.mix(fill, p.panel, 0.65) if self._dimmed else fill

    def retranslate(self) -> None:
        p = theme.current()
        self.name.setText(t("panel.iphone" if self.side == "iphone" else "panel.android"))
        self.state.setText(t(f"panel.state.{self._state}"))
        on_fill = self._header_fill() != p.panel
        header_color = p.text_muted if self._dimmed else (p.on_accent if on_fill else p.text)
        self.name.setStyleSheet(f"color: {header_color};")
        self.state.setStyleSheet(f"color: {header_color};")
        body_color = p.text_muted if self._dimmed else p.text
        for label, text in zip(self.facts, self._facts + ["", "", ""]):
            label.setText(text)
            label.setVisible(bool(text) and not self._compact)
            label.setStyleSheet(f"color: {body_color};")
        self.status.setText(self._status)
        self.status.setVisible(bool(self._status) and not self._compact)
        self.update()

    def paintEvent(self, _event) -> None:
        p = theme.current()
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        r = theme.PANEL_RADIUS
        outer = QRectF(0.5, 0.5, self.width() - 1, self.height() - 1)
        path = QPainterPath()
        path.addRoundedRect(outer, r, r)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor(p.panel))
        painter.drawPath(path)
        fill = self._header_fill()
        painter.save()
        painter.setClipPath(path)
        painter.setBrush(QColor(fill))
        painter.drawRect(QRectF(0, 0, self.width(), HEADER_H))
        painter.restore()
        if fill == p.panel:
            painter.setPen(QPen(QColor(p.line), 1))
            painter.drawLine(1, HEADER_H, self.width() - 1, HEADER_H)
        painter.setPen(QPen(QColor(p.line), 1))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawPath(path)
        painter.end()
