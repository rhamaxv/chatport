"""A card showing one running job: phase, bar, percent, time left, bytes and a cancel button."""
from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QHBoxLayout, QLabel, QProgressBar, QPushButton, QWidget

from chatport.i18n import t
from chatport.ui import format as fmt
from chatport.ui.widgets.cards import Card


class ProgressCard(Card):
    cancelled = Signal()

    def __init__(self, parent: QWidget | None = None, cancellable: bool = True):
        super().__init__(parent, padding=20, spacing=12)
        top = QHBoxLayout()
        self.phase = QLabel()
        self.phase.setProperty("role", "heading")
        self.percent = QLabel()
        self.percent.setProperty("role", "heading")
        top.addWidget(self.phase, 1)
        top.addWidget(self.percent, 0, Qt.AlignmentFlag.AlignRight)
        self.body.addLayout(top)
        self.bar = QProgressBar()
        self.bar.setRange(0, 1000)
        self.bar.setTextVisible(False)
        self.body.addWidget(self.bar)
        bottom = QHBoxLayout()
        self.detail = QLabel()
        self.detail.setProperty("role", "muted")
        bottom.addWidget(self.detail, 1)
        self.cancel_button = QPushButton()
        self.cancel_button.setProperty("variant", "quiet")
        self.cancel_button.setVisible(cancellable)
        self.cancel_button.clicked.connect(self._cancel)
        bottom.addWidget(self.cancel_button, 0, Qt.AlignmentFlag.AlignRight)
        self.body.addLayout(bottom)
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
        if self._pct is None:
            self.bar.setRange(0, 0)
            self.percent.setText("")
        else:
            self.bar.setRange(0, 1000)
            self.bar.setValue(int(max(0.0, min(100.0, self._pct)) * 10))
            self.percent.setText(t("progress.percent", pct=int(self._pct)))
        parts = []
        if self._done_bytes is not None and self._total_bytes:
            parts.append(t("progress.bytes", done=fmt.bytes_text(self._done_bytes), total=fmt.bytes_text(self._total_bytes)))
        if self._eta is not None and self._pct is not None and self._pct < 100:
            parts.append(t("progress.eta", eta=fmt.duration(self._eta)))
        self.detail.setText("   ".join(parts))
        self.cancel_button.setText(t("progress.cancelling") if self._cancelling else t("progress.cancel"))
