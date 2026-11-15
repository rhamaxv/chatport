"""Explains one ErrorCode in plain words and offers the one action that helps."""
from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QPushButton, QVBoxLayout, QWidget

from chatport.core.errors import ACTION, ACTION_TARGET, ErrorCode
from chatport.i18n import t
from chatport.ui.widgets.cards import Card, Chip

ACTION_LABEL = {"retry": "common.try_again", "back": "common.go_back", "guide": "common.show_how", "log": "common.copy_log"}


def code_of(data: dict) -> ErrorCode:
    try:
        return ErrorCode(data.get("code", "unknown"))
    except ValueError:
        return ErrorCode.UNKNOWN


class ErrorCard(Card):
    """`action(kind, target)` fires with kind in retry/back/guide/log; `copy_log` fires for the log button."""

    action = Signal(str, str)
    copy_log = Signal()

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent, padding=20, spacing=12)
        self.body.setContentsMargins(18, 18, 22, 18)
        self.set_tone("danger")
        self.code = ErrorCode.UNKNOWN
        self.detail = ""
        self.kind = "none"
        row = QHBoxLayout()
        row.setSpacing(16)
        self.bar = QFrame()
        self.bar.setObjectName("errorbar")
        row.addWidget(self.bar, 0)
        self.icon = Chip("alert", 40, "rose")
        row.addWidget(self.icon, 0, Qt.AlignmentFlag.AlignTop)
        text = QVBoxLayout()
        text.setSpacing(6)
        self.title = QLabel()
        self.title.setProperty("role", "heading")
        self.title.setWordWrap(True)
        self.text = QLabel()
        self.text.setWordWrap(True)
        self.text.setProperty("role", "muted")
        self.extra = QLabel()
        self.extra.setWordWrap(True)
        self.extra.setProperty("role", "mono")
        self.extra.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        text.addWidget(self.title)
        text.addWidget(self.text)
        text.addWidget(self.extra)
        text.addSpacing(6)
        buttons = QHBoxLayout()
        buttons.setSpacing(8)
        self.button = QPushButton()
        self.button.clicked.connect(self._primary)
        self.log_button = QPushButton()
        self.log_button.setProperty("variant", "quiet")
        self.log_button.clicked.connect(self.copy_log.emit)
        buttons.addWidget(self.button)
        buttons.addWidget(self.log_button)
        buttons.addStretch(1)
        text.addLayout(buttons)
        row.addLayout(text, 1)
        self.body.addLayout(row)

    def show_error(self, data: dict, fallback_action: str | None = None) -> None:
        self.code = code_of(data)
        self.detail = str(data.get("detail") or "")
        self.kind = ACTION.get(self.code, "log")
        if self.kind == "none" and fallback_action:
            self.kind = fallback_action
        self.retranslate()

    def retranslate(self) -> None:
        code = self.code.value
        self.title.setText(t(f"error.{code}.title"))
        body = t(f"error.{code}.body")
        if self.code in (ErrorCode.UNKNOWN, ErrorCode.BUILD_FAILED) and self.detail:
            self.extra.setText(self.detail[:300])
            self.extra.setVisible(True)
        else:
            self.extra.setVisible(False)
        self.text.setText(body)
        action_key = f"error.{code}.action"
        label = t(action_key)
        if label == action_key:
            label = t(ACTION_LABEL.get(self.kind, "common.ok"))
        self.button.setText(label)
        self.button.setVisible(self.kind != "none")
        self.button.setProperty("variant", "primary" if self.kind in ("retry", "back") else "")
        self.log_button.setText(t("common.copy_log"))
        self.log_button.setVisible(self.kind == "log" or self.code == ErrorCode.UNKNOWN)
        if self.kind == "log":
            self.button.setVisible(False)
        from chatport.ui import theme

        theme.repolish(self.button)
        self.icon.refresh()

    def _primary(self) -> None:
        if self.kind == "log":
            self.copy_log.emit()
            return
        self.action.emit(self.kind, ACTION_TARGET.get(self.code, ""))
