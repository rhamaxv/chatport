"""Asks for the iPhone backup password. Masked by default, with a show toggle. Never stored."""
from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QDialog, QHBoxLayout, QLabel, QLineEdit, QPushButton, QVBoxLayout, QWidget

from chatport.i18n import t


class PasswordDialog(QDialog):
    def __init__(self, parent: QWidget | None = None, wrong: bool = False):
        super().__init__(parent)
        self.setWindowTitle(t("backup.password.title"))
        self.setModal(True)
        self.setMinimumWidth(420)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 28, 28, 24)
        layout.setSpacing(14)
        title = QLabel(t("backup.password.title"))
        title.setProperty("role", "heading")
        body = QLabel(t("backup.password.wrong") if wrong else t("backup.password.body"))
        body.setWordWrap(True)
        body.setProperty("role", "muted")
        layout.addWidget(title)
        layout.addWidget(body)
        row = QHBoxLayout()
        self.edit = QLineEdit()
        self.edit.setEchoMode(QLineEdit.EchoMode.Password)
        self.edit.setPlaceholderText(t("backup.password.placeholder"))
        self.edit.textChanged.connect(lambda s: self.ok.setEnabled(bool(s)))
        self.show_button = QPushButton(t("backup.password.show"))
        self.show_button.setProperty("variant", "quiet")
        self.show_button.setCheckable(True)
        self.show_button.toggled.connect(self._toggle)
        row.addWidget(self.edit, 1)
        row.addWidget(self.show_button)
        layout.addLayout(row)
        buttons = QHBoxLayout()
        buttons.addStretch(1)
        cancel = QPushButton(t("common.cancel"))
        cancel.setProperty("variant", "quiet")
        cancel.clicked.connect(self.reject)
        self.ok = QPushButton(t("common.continue"))
        self.ok.setProperty("variant", "primary")
        self.ok.setEnabled(False)
        self.ok.setDefault(True)
        self.ok.clicked.connect(self.accept)
        buttons.addWidget(cancel)
        buttons.addWidget(self.ok)
        layout.addLayout(buttons)
        self.edit.setFocus()

    def _toggle(self, show: bool) -> None:
        self.edit.setEchoMode(QLineEdit.EchoMode.Normal if show else QLineEdit.EchoMode.Password)
        self.show_button.setText(t("backup.password.hide") if show else t("backup.password.show"))

    def password(self) -> str:
        return self.edit.text()

    @staticmethod
    def ask(parent: QWidget | None, wrong: bool = False) -> str | None:
        dialog = PasswordDialog(parent, wrong)
        if dialog.exec() == QDialog.DialogCode.Accepted and dialog.password():
            return dialog.password()
        return None
