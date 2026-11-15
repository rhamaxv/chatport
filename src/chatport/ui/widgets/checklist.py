"""Rows the person ticks off, each optionally carrying a live check result shown as a pill on the right."""
from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QCheckBox, QFrame, QHBoxLayout, QLabel, QVBoxLayout, QWidget

from chatport.i18n import t
from chatport.ui.widgets.cards import Card, IconLabel, Pill


class ChecklistRow(QWidget):
    def __init__(self, key: str, text_key: str, manual: bool = True, parent: QWidget | None = None,
                 note_key: str | None = None):
        super().__init__(parent)
        self.key = key
        self.text_key = text_key
        self.manual = manual
        self._static_note = note_key  # always shown, e.g. how to do this on the phone
        self._note_key = note_key
        self.live: bool | None = None
        row = QHBoxLayout(self)
        row.setContentsMargins(0, 10, 0, 10)
        row.setSpacing(14)
        self.box = QCheckBox()
        self.box.setVisible(manual)
        self.check = IconLabel("check", 20, "accent")      # live row, verified
        self.warn = IconLabel("alert", 20, "amber")        # live row, not yet
        self.check.setVisible(False)
        self.warn.setVisible(not manual)
        row.addWidget(self.box, 0, Qt.AlignmentFlag.AlignTop)
        row.addWidget(self.check, 0, Qt.AlignmentFlag.AlignTop)
        row.addWidget(self.warn, 0, Qt.AlignmentFlag.AlignTop)
        text = QVBoxLayout()
        text.setSpacing(3)
        self.label = QLabel()
        self.label.setWordWrap(True)
        self.note = QLabel()
        self.note.setWordWrap(True)
        self.note.setProperty("role", "caption")
        self.note.setVisible(bool(note_key))
        text.addWidget(self.label)
        text.addWidget(self.note)
        row.addLayout(text, 1)
        self.pill = Pill("checking")
        self.pill.setVisible(False)
        row.addWidget(self.pill, 0, Qt.AlignmentFlag.AlignTop)
        self.retranslate()

    def set_live(self, ok: bool | None, note_key: str | None = None) -> None:
        self.live = ok
        self.pill.setVisible(ok is not None)
        self.pill.set_kind("ready" if ok else "attention")
        self._note_key = note_key or self._static_note
        self.note.setVisible(bool(self._note_key))
        if not self.manual:  # a live row is decided by the phone, a manual row only by the person
            self.check.setVisible(ok is True)
            self.warn.setVisible(ok is not True)
        self.retranslate()

    def checked(self) -> bool:
        return self.box.isChecked() if self.manual else self.live is True

    def retranslate(self) -> None:
        self.label.setText(t(self.text_key))
        key = getattr(self, "_note_key", None)
        self.note.setText(t(key) if key else "")
        self.pill.retranslate()
        self.check.refresh()
        self.warn.refresh()


class Checklist(Card):
    changed = Signal()

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent, padding=18, spacing=0)
        self.body.setContentsMargins(22, 8, 22, 8)
        self.rows: dict[str, ChecklistRow] = {}

    def add(self, key: str, text_key: str, manual: bool = True, note_key: str | None = None) -> ChecklistRow:
        if self.rows:
            divider = QFrame(self)
            divider.setProperty("divider", True)
            self.body.addWidget(divider)
        row = ChecklistRow(key, text_key, manual, self, note_key=note_key)
        row.box.toggled.connect(lambda _c: self.changed.emit())
        self.rows[key] = row
        self.body.addWidget(row)
        return row

    def set_live(self, key: str, ok: bool | None, note_key: str | None = None) -> None:
        if key in self.rows:
            self.rows[key].set_live(ok, note_key)
            self.changed.emit()

    def all_checked(self) -> bool:
        return all(r.checked() for r in self.rows.values())

    def reset(self) -> None:
        for row in self.rows.values():
            row.box.setChecked(False)
            row.set_live(None)
        self.changed.emit()

    def retranslate(self) -> None:
        for row in self.rows.values():
            row.retranslate()
