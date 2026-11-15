"""Rows the person ticks off, separated by 1 px lines. Live rows are decided by the iPhone and show a lime
check or an ink circle; manual rows show a square checkbox."""
from __future__ import annotations

from PySide6.QtCore import QRectF, Qt, Signal
from PySide6.QtGui import QColor, QPainter, QPen
from PySide6.QtWidgets import QCheckBox, QFrame, QHBoxLayout, QLabel, QVBoxLayout, QWidget

from chatport.i18n import t
from chatport.ui import icons, theme

MARK = 20


class LiveMark(QWidget):
    """A lime circle with an ink check once the iPhone confirms, an ink circle until then."""

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self._ok: bool | None = None
        self.setFixedSize(MARK, MARK)

    def set_ok(self, ok: bool | None) -> None:
        self._ok = ok
        self.update()

    def paintEvent(self, _event) -> None:
        p = theme.current()
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        rect = QRectF(1, 1, MARK - 2, MARK - 2)
        if self._ok is True:
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QColor(p.lime))
            painter.drawEllipse(rect)
            painter.drawPixmap(3, 3, icons.pixmap("check", 14, p.on_accent, self.devicePixelRatioF()))
        else:
            painter.setPen(QPen(QColor(p.text), 1.5))
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawEllipse(rect)
        painter.end()


class FocusBox(QCheckBox):
    """A checkbox whose indicator gets a 2 px ink border while it has keyboard focus (styled by `focused`)."""

    def focusInEvent(self, event) -> None:
        super().focusInEvent(event)
        self.setProperty("focused", True)
        theme.repolish(self)

    def focusOutEvent(self, event) -> None:
        super().focusOutEvent(event)
        self.setProperty("focused", False)
        theme.repolish(self)


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
        row.setContentsMargins(0, 12, 0, 12)
        row.setSpacing(14)
        self.box = FocusBox()
        self.box.setVisible(manual)
        self.mark = LiveMark()
        self.mark.setVisible(not manual)
        row.addWidget(self.box, 0, Qt.AlignmentFlag.AlignTop)
        row.addWidget(self.mark, 0, Qt.AlignmentFlag.AlignTop)
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
        self.retranslate()

    def set_live(self, ok: bool | None, note_key: str | None = None) -> None:
        self.live = ok
        self._note_key = note_key or self._static_note
        self.note.setVisible(bool(self._note_key))
        if not self.manual:  # a live row is decided by the phone, a manual row only by the person
            self.mark.set_ok(ok)
        self.retranslate()

    def checked(self) -> bool:
        return self.box.isChecked() if self.manual else self.live is True

    def retranslate(self) -> None:
        self.label.setText(t(self.text_key))
        key = getattr(self, "_note_key", None)
        self.note.setText(t(key) if key else "")
        self.mark.update()


class Checklist(QWidget):
    changed = Signal()

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.body = QVBoxLayout(self)
        self.body.setContentsMargins(0, 0, 0, 0)
        self.body.setSpacing(0)
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
