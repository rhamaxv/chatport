"""Sixteen boxes of four hex digits. Typing advances, pasting a whole key fills every box."""
from __future__ import annotations

from PySide6.QtCore import QEvent, Qt, Signal
from PySide6.QtGui import QColor, QKeySequence
from PySide6.QtWidgets import QApplication, QGraphicsDropShadowEffect, QGridLayout, QLineEdit, QWidget

from chatport.core.keygrid import GROUP, GROUPS, PER_ROW, normalize

HEX = set("0123456789abcdef")


class KeyBox(QLineEdit):
    def __init__(self, index: int, parent: "KeyGrid"):
        super().__init__(parent)
        self.index = index
        self.grid = parent
        self.setMaxLength(GROUP)
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setProperty("role", "key")
        self.setPlaceholderText("0000")
        self.setFixedHeight(48)

    def keyPressEvent(self, event) -> None:
        if event.matches(QKeySequence.StandardKey.Paste):
            self.grid.paste(QApplication.clipboard().text())
            return
        key = event.key()
        if key == Qt.Key.Key_Backspace and not self.text() and self.index > 0:
            prev = self.grid.boxes[self.index - 1]
            prev.setFocus()
            prev.setText(prev.text()[:-1])
            return
        if key in (Qt.Key.Key_Left,) and self.cursorPosition() == 0 and self.index > 0:
            self.grid.boxes[self.index - 1].setFocus()
            return
        if key in (Qt.Key.Key_Right,) and self.cursorPosition() == len(self.text()) and self.index < GROUPS - 1:
            self.grid.boxes[self.index + 1].setFocus()
            return
        text = event.text()
        if text and not event.modifiers() & (Qt.KeyboardModifier.ControlModifier | Qt.KeyboardModifier.MetaModifier):
            if len(text) > 1:
                self.grid.paste(text)
                return
            if text.lower() in HEX:
                if len(self.text()) >= GROUP and self.index < GROUPS - 1 and not self.hasSelectedText():
                    nxt = self.grid.boxes[self.index + 1]
                    nxt.setFocus()
                    nxt.insert(text.lower())
                    return
                super().keyPressEvent(event)
                self.setText(self.text().lower())
                return
            if text.strip() in ("", "-", ":", ".", "|"):
                return
            if text.isprintable():
                return
        super().keyPressEvent(event)

    def event(self, event) -> bool:
        if event.type() == QEvent.Type.FocusIn:
            if self.text():
                self.selectAll()
            self._glow(True)
        elif event.type() == QEvent.Type.FocusOut:
            self._glow(False)
        return super().event(event)

    def _glow(self, on: bool) -> None:
        """A soft accent halo while the box has focus. Setting None drops the old effect."""
        if not on:
            self.setGraphicsEffect(None)
            return
        from chatport.ui import theme

        color = QColor(theme.current().rose if self.property("invalid") else theme.current().accent)
        color.setAlphaF(0.6)
        effect = QGraphicsDropShadowEffect(self)
        effect.setBlurRadius(22)
        effect.setOffset(0, 0)
        effect.setColor(color)
        self.setGraphicsEffect(effect)


class KeyGrid(QWidget):
    changed = Signal(str)

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        layout = QGridLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setHorizontalSpacing(10)
        layout.setVerticalSpacing(10)
        self.boxes: list[KeyBox] = []
        for i in range(GROUPS):
            box = KeyBox(i, self)
            box.textChanged.connect(self._on_text_changed)
            layout.addWidget(box, i // PER_ROW, i % PER_ROW)
            self.boxes.append(box)
        self._muted = False

    def text(self) -> str:
        return "".join(b.text() for b in self.boxes)

    def set_text(self, value: str) -> None:
        clean = normalize(value)[: GROUP * GROUPS]
        self._muted = True
        for i, box in enumerate(self.boxes):
            box.setText(clean[i * GROUP:(i + 1) * GROUP])
        self._muted = False
        self._emit()

    def paste(self, raw: str) -> None:
        clean = "".join(ch for ch in normalize(raw) if ch in HEX)
        if not clean:
            return
        focused = next((b.index for b in self.boxes if b.hasFocus()), 0)
        start = 0 if len(clean) >= GROUP * GROUPS else focused
        self._muted = True
        pos = start * GROUP + (len(self.boxes[start].text()) if len(clean) < GROUP * GROUPS else 0)
        current = list(self.text().ljust(GROUP * GROUPS))
        for ch in clean:
            if pos >= GROUP * GROUPS:
                break
            current[pos] = ch
            pos += 1
        joined = "".join(current).rstrip()
        for i, box in enumerate(self.boxes):
            box.setText(joined[i * GROUP:(i + 1) * GROUP].strip())
        self._muted = False
        target = min(pos // GROUP, GROUPS - 1)
        self.boxes[target].setFocus()
        self.boxes[target].setCursorPosition(len(self.boxes[target].text()))
        self._emit()

    def clear(self) -> None:
        self.set_text("")

    def set_invalid(self, invalid: bool) -> None:
        from chatport.ui import theme

        for box in self.boxes:
            box.setProperty("invalid", invalid)
            theme.repolish(box)
            if box.hasFocus():
                box._glow(True)

    def set_enabled(self, enabled: bool) -> None:
        for box in self.boxes:
            box.setEnabled(enabled)

    def is_complete(self) -> bool:
        text = self.text()
        return len(text) == GROUP * GROUPS and all(ch in HEX for ch in text)

    def _on_text_changed(self, _text: str) -> None:
        if self._muted:
            return
        sender = self.sender()
        if isinstance(sender, KeyBox) and len(sender.text()) == GROUP and sender.index < GROUPS - 1:
            if sender.cursorPosition() == GROUP:
                self.boxes[sender.index + 1].setFocus()
        self._emit()

    def _emit(self) -> None:
        self.changed.emit(self.text())
