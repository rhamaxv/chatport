"""Explains one ErrorCode in plain words: rose title, body, and the one action that helps."""
from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QPushButton, QVBoxLayout, QWidget

from chatport.core.errors import ACTION, ACTION_TARGET, ErrorCode
from chatport.i18n import t
from chatport.ui import theme

ACTION_LABEL = {"retry": "common.try_again", "back": "common.go_back", "guide": "common.show_how", "log": "common.copy_log"}


def code_of(data: dict) -> ErrorCode:
    try:
        return ErrorCode(data.get("code", "unknown"))
    except ValueError:
        return ErrorCode.UNKNOWN


class ErrorCard(QFrame):
    """`action(kind, target)` fires with kind in retry/back/guide/log; `copy_log` fires for the log button."""

    action = Signal(str, str)
    copy_log = Signal()

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.setProperty("surface", True)
        self.setProperty("tone", "error")
        self.code = ErrorCode.UNKNOWN
        self.detail = ""
        self.kind = "none"
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(8)
        self.title = QLabel()
        self.title.setProperty("role", "error-title")
        self.title.setWordWrap(True)
        self.text = QLabel()
        self.text.setWordWrap(True)
        self.extra = QLabel()
        self.extra.setWordWrap(True)
        self.extra.setProperty("role", "mono")
        self.extra.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        layout.addWidget(self.title)
        layout.addWidget(self.text)
        layout.addWidget(self.extra)
        buttons = QHBoxLayout()
        buttons.setContentsMargins(0, 8, 0, 0)
        buttons.setSpacing(8)
        self.button = QPushButton()
        self.button.clicked.connect(self._primary)
        self.log_button = QPushButton()
        self.log_button.clicked.connect(self.copy_log.emit)
        buttons.addWidget(self.button)
        buttons.addWidget(self.log_button)
        buttons.addStretch(1)
        layout.addLayout(buttons)

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
        self.text.setText(t(f"error.{code}.body"))
        show_detail = self.code in (ErrorCode.UNKNOWN, ErrorCode.BUILD_FAILED) and bool(self.detail)
        self.extra.setText(self.detail[:300] if show_detail else "")
        self.extra.setVisible(show_detail)
        action_key = f"error.{code}.action"
        label = t(action_key)
        if label == action_key:
            label = t(ACTION_LABEL.get(self.kind, "common.ok"))
        self.button.setText(label)
        self.button.setProperty("variant", "primary" if self.kind in ("retry", "back") else "")
        theme.repolish(self.button)
        self.log_button.setText(t("common.copy_log"))
        # Exactly one button: the log button stands in for the action when the action is the log itself.
        self.log_button.setVisible(self.kind == "log")
        self.button.setVisible(self.kind not in ("none", "log"))

    def _primary(self) -> None:
        self.action.emit(self.kind, ACTION_TARGET.get(self.code, ""))
