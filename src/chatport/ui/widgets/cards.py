"""Card surfaces and the small tinted pieces that live on them: icon chips, status pills, stat tiles."""
from __future__ import annotations

from PySide6.QtCore import QEvent, QRectF, QSize, Qt
from PySide6.QtGui import QColor, QFont, QPainter
from PySide6.QtWidgets import QFrame, QGraphicsDropShadowEffect, QHBoxLayout, QLabel, QSizePolicy, QVBoxLayout, QWidget

from chatport.ui import icons, theme

TONES = {"green": "success", "amber": "warning", "red": "danger", "gray": "text_muted"}
# Tone names used by StatusCard / checklist rows, mapped to pill kinds.
PILL_OF_TONE = {"green": "ready", "amber": "attention", "red": "problem", "gray": "checking"}
PILL_HUE = {"ready": "teal", "attention": "amber", "problem": "rose", "checking": "muted"}
PILL_KEY = {"ready": "pill.ready", "attention": "pill.attention", "problem": "pill.problem", "checking": "pill.checking"}


class Card(QFrame):
    """A surface with a soft drop shadow. `nested=True` gives a flat surface2 panel for use inside another card."""

    def __init__(self, parent: QWidget | None = None, padding: int = 20, spacing: int = 10, nested: bool = False):
        super().__init__(parent)
        self.setProperty("card", True)
        self.setProperty("nested", nested)
        # Preferred, not Maximum: word-wrapped labels report heightForWidth, and a Maximum policy would
        # pin the card to the unwrapped size hint and clip them.
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        self.body = QVBoxLayout(self)
        self.body.setContentsMargins(padding, padding, padding, padding)
        self.body.setSpacing(spacing)
        self._shadow: QGraphicsDropShadowEffect | None = None
        if not nested:
            self._shadow = QGraphicsDropShadowEffect(self)
            self._shadow.setBlurRadius(24)
            self._shadow.setOffset(0, 6)
            self._shadow.setColor(theme.current().shadow())
            self.setGraphicsEffect(self._shadow)

    def set_tone(self, tone: str | None) -> None:
        self.setProperty("tone", tone or "")
        theme.repolish(self)

    def changeEvent(self, event) -> None:
        if event.type() == QEvent.Type.StyleChange and self._shadow is not None:
            self._shadow.setColor(theme.current().shadow())
        super().changeEvent(event)


class Dot(QWidget):
    """A small filled circle in a semantic color."""

    def __init__(self, color_key: str = "text_muted", size: int = 10, parent: QWidget | None = None):
        super().__init__(parent)
        self._key = color_key
        self._size = size
        self.setFixedSize(size, size)

    def set_color(self, color_key: str) -> None:
        self._key = color_key
        self.update()

    def paintEvent(self, _event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor(theme.current().hue(self._key)))
        painter.drawEllipse(0, 0, self._size, self._size)
        painter.end()


class IconLabel(QLabel):
    def __init__(self, name: str, size: int = 24, color_key: str = "text", parent: QWidget | None = None):
        super().__init__(parent)
        self._name, self._size, self._key = name, size, color_key
        self.setFixedSize(size, size)
        self.refresh()

    def set_icon(self, name: str, color_key: str | None = None) -> None:
        self._name = name
        if color_key:
            self._key = color_key
        self.refresh()

    def refresh(self) -> None:
        color = theme.current().hue(self._key)
        dpr = self.devicePixelRatioF() if self.windowHandle() else 2.0
        self.setPixmap(icons.pixmap(self._name, self._size, color, dpr))


class Chip(QWidget):
    """An icon on a tinted rounded square (or circle). The hue follows the icon unless given."""

    def __init__(self, name: str, size: int = 40, hue: str | None = None, parent: QWidget | None = None,
                 circle: bool = False):
        super().__init__(parent)
        self._name = name
        self._hue = hue or theme.ICON_HUES.get(name, "teal")
        self._size = size
        self._circle = circle
        self.setFixedSize(size, size)

    def set_icon(self, name: str, hue: str | None = None) -> None:
        self._name = name
        self._hue = hue or theme.ICON_HUES.get(name, "teal")
        self.update()

    def set_hue(self, hue: str) -> None:
        self._hue = hue
        self.update()

    def refresh(self) -> None:
        self.update()

    def paintEvent(self, _event) -> None:
        p = theme.current()
        color = QColor(p.hue(self._hue))
        fill = QColor(color)
        fill.setAlphaF(p.chip_alpha)
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(fill)
        rect = QRectF(0, 0, self._size, self._size)
        if self._circle:
            painter.drawEllipse(rect)
        else:
            radius = 10 if self._size <= 44 else round(self._size * 0.26)
            painter.drawRoundedRect(rect, radius, radius)
        icon_size = max(16, round(self._size * 0.5))
        pm = icons.pixmap(self._name, icon_size, color.name(), self.devicePixelRatioF())
        offset = (self._size - icon_size) / 2
        painter.drawPixmap(int(offset), int(offset), pm)
        painter.end()


class Pill(QWidget):
    """A rounded status label: Ready, Needs attention, Problem, Checking. Text comes from i18n."""

    HEIGHT = 22
    PAD = 10

    def __init__(self, kind: str = "checking", parent: QWidget | None = None):
        super().__init__(parent)
        self._kind = kind
        self._text = ""
        self.setFixedHeight(self.HEIGHT)
        self.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        self.retranslate()

    def kind(self) -> str:
        return self._kind

    def set_kind(self, kind: str) -> None:
        self._kind = kind if kind in PILL_HUE else "checking"
        self.retranslate()

    def set_tone(self, tone: str) -> None:
        self.set_kind(PILL_OF_TONE.get(tone, "checking"))

    def _font(self) -> QFont:
        font = QFont(self.font())
        font.setPixelSize(12)
        font.setWeight(QFont.Weight.DemiBold)
        return font

    def retranslate(self) -> None:
        from chatport.i18n import t

        self._text = t(PILL_KEY[self._kind])
        self.updateGeometry()
        self.update()

    def sizeHint(self) -> QSize:
        from PySide6.QtGui import QFontMetrics

        width = QFontMetrics(self._font()).horizontalAdvance(self._text) + 2 * self.PAD
        return QSize(width, self.HEIGHT)

    def minimumSizeHint(self) -> QSize:
        return self.sizeHint()

    def paintEvent(self, _event) -> None:
        p = theme.current()
        color = QColor(p.hue(PILL_HUE[self._kind]))
        fill = QColor(color)
        fill.setAlphaF(0.16 if p.dark else 0.13)
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setRenderHint(QPainter.RenderHint.TextAntialiasing)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(fill)
        rect = QRectF(0, 0, self.width(), self.height())
        painter.drawRoundedRect(rect, self.HEIGHT / 2, self.HEIGHT / 2)
        painter.setFont(self._font())
        painter.setPen(color if p.dark else QColor(theme.mix(color.name(), "#000000", 0.12)))
        painter.drawText(rect, Qt.AlignmentFlag.AlignCenter, self._text)
        painter.end()


class Tile(Card):
    """A nested stat tile: a big number over a small caption."""

    def __init__(self, caption_key: str, parent: QWidget | None = None):
        super().__init__(parent, padding=14, spacing=2, nested=True)
        self.caption_key = caption_key
        self.value = QLabel("0")
        self.value.setProperty("role", "stat")
        self.caption = QLabel()
        self.caption.setProperty("role", "caption")
        self.caption.setWordWrap(True)
        self.body.addWidget(self.value)
        self.body.addWidget(self.caption)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        self.retranslate()

    def set_value(self, text: str) -> None:
        self.value.setText(text)

    def retranslate(self) -> None:
        from chatport.i18n import t

        self.caption.setText(t(self.caption_key))


class StatusCard(Card):
    """Icon chip on the left, a title and status lines, a status pill on the right."""

    def __init__(self, icon_name: str, parent: QWidget | None = None):
        super().__init__(parent, padding=18, spacing=0)
        row = QHBoxLayout()
        row.setSpacing(16)
        self.icon = Chip(icon_name, 44)
        row.addWidget(self.icon, 0, Qt.AlignmentFlag.AlignTop)
        text = QVBoxLayout()
        text.setSpacing(4)
        self.title = QLabel()
        self.title.setProperty("role", "heading")
        self.status = QLabel()
        self.status.setProperty("role", "muted")
        self.status.setWordWrap(True)
        text.addWidget(self.title)
        text.addWidget(self.status)
        row.addLayout(text, 1)
        self.pill = Pill("checking")
        row.addWidget(self.pill, 0, Qt.AlignmentFlag.AlignTop)
        self.body.addLayout(row)
        self.extra = QVBoxLayout()
        self.extra.setContentsMargins(60, 0, 0, 0)
        self.extra.setSpacing(8)
        self.body.addLayout(self.extra)

    def set_state(self, title: str, status: str, tone: str = "gray") -> None:
        self.title.setText(title)
        self.status.setText(status)
        self.pill.set_tone(tone)
        self.icon.refresh()

    def retranslate(self) -> None:
        self.pill.retranslate()
