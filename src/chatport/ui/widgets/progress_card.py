"""A card showing one running job: phase, bar, a big percent, and small chips for time left and bytes."""
from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QHBoxLayout, QLabel, QPushButton, QWidget

from chatport.i18n import t
from chatport.ui import format as fmt
from chatport.ui.widgets.cards import Card
from chatport.ui.widgets.progress_bar import SlimBar


class InfoChip(QLabel):
    """A small surface2 pill with 12 px text, for the ETA and the byte count. Styled by the app sheet."""

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.setProperty("infochip", True)
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)


class ProgressCard(Card):
    cancelled = Signal()

    def __init__(self, parent: QWidget | None = None, cancellable: bool = True):
        super().__init__(parent, padding=22, spacing=12)
        top = QHBoxLayout()
        top.setSpacing(16)
        self.phase = QLabel()
        self.phase.setProperty("role", "heading")
        self.phase.setWordWrap(True)
        self.percent = QLabel()
        self.percent.setProperty("role", "percent")
        self.percent.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        top.addWidget(self.phase, 1, Qt.AlignmentFlag.AlignVCenter)
        top.addWidget(self.percent, 0, Qt.AlignmentFlag.AlignVCenter)
        self.body.addLayout(top)
        self.bar = SlimBar()
        self.body.addWidget(self.bar)
        bottom = QHBoxLayout()
        bottom.setSpacing(8)
        self.eta_chip = InfoChip()
        self.bytes_chip = InfoChip()
        bottom.addWidget(self.bytes_chip, 0)
        bottom.addWidget(self.eta_chip, 0)
        bottom.addStretch(1)
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
        self.bar.set_value(self._pct)
        self.percent.setText("" if self._pct is None else t("progress.percent", pct=int(self._pct)))
        self.percent.setVisible(self._pct is not None)
        has_bytes = self._done_bytes is not None and bool(self._total_bytes)
        self.bytes_chip.setVisible(has_bytes)
        if has_bytes:
            self.bytes_chip.setText(t("progress.bytes", done=fmt.bytes_text(self._done_bytes), total=fmt.bytes_text(self._total_bytes)))
        has_eta = self._eta is not None and self._pct is not None and self._pct < 100
        self.eta_chip.setVisible(has_eta)
        if has_eta:
            self.eta_chip.setText(t("progress.eta", eta=fmt.duration(self._eta)))
        self.cancel_button.setText(t("progress.cancelling") if self._cancelling else t("progress.cancel"))
