"""The two Bridge palettes (paper/ink and graphite/bone) and the application stylesheet.

One lime signal for whatever moves right now, lavender for the iPhone side, rose for error text and
borders only. No gradients, no shadows, no glow: depth is the panel color against the background
plus 1 px lines. Headings are Bricolage Grotesque, body is Inter.
"""
from __future__ import annotations

import os
from dataclasses import dataclass

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QGuiApplication, QPalette
from PySide6.QtWidgets import QApplication

FONT_FAMILY = "Inter"
HEADING_FAMILY = "Bricolage Grotesque"
MONO_FAMILY = '"SF Mono", Menlo, Consolas, "DejaVu Sans Mono", monospace'

PANEL_WIDTH = 260
PANEL_RADIUS = 18
TILE_RADIUS = 14
PAGE_PADDING = 40

INK = "#1B1C1A"
LIME = "#D6F55A"
LAVENDER = "#CBB9FF"
ROSE = "#E0553F"


def rgba(color: str, alpha: float) -> str:
    c = QColor(color)
    return f"rgba({c.red()}, {c.green()}, {c.blue()}, {alpha:.3f})"


def mix(a: str, b: str, amount: float) -> str:
    """Blend color a toward color b by amount (0..1)."""
    ca, cb = QColor(a), QColor(b)
    r = round(ca.red() + (cb.red() - ca.red()) * amount)
    g = round(ca.green() + (cb.green() - ca.green()) * amount)
    bl = round(ca.blue() + (cb.blue() - ca.blue()) * amount)
    return QColor(r, g, bl).name()


@dataclass(frozen=True)
class Palette:
    bg: str
    panel: str
    line: str
    text: str
    text_muted: str
    dark: bool = False
    lime: str = LIME
    lavender: str = LAVENDER
    rose: str = ROSE
    on_accent: str = INK          # ink on lime and on lavender in both themes

    @property
    def accent(self) -> str:
        return self.lime

    @property
    def warn(self) -> str:
        """Lime at 30 percent over the panel: the warning surface, with the theme's text color on it."""
        return mix(self.panel, self.lime, 0.30)

    def shade(self, color: str, amount: float) -> str:
        """Hover and pressed states: darker on paper, lighter on graphite, so the change is visible."""
        return mix(color, "#FFFFFF" if self.dark else "#000000", amount)

    def line_strong(self) -> str:
        return mix(self.line, self.text, 0.25)


LIGHT = Palette(bg="#F4F1EA", panel="#FFFFFF", line="#D9D4C7", text=INK, text_muted=mix(INK, "#F4F1EA", 0.30))
DARK = Palette(bg="#141516", panel="#1E1F21", line="#2E3033", text="#ECEAE3",
               text_muted=mix("#ECEAE3", "#141516", 0.30), dark=True)

_current = LIGHT


def palette(dark: bool) -> Palette:
    return DARK if dark else LIGHT


def current() -> Palette:
    return _current


def os_prefers_dark() -> bool:
    forced = os.environ.get("CHATPORT_THEME", "").strip().lower()
    if forced in ("light", "dark"):
        return forced == "dark"
    try:
        return QGuiApplication.styleHints().colorScheme() == Qt.ColorScheme.Dark
    except Exception:
        return False


def _check_url() -> str:
    from .icons import svg_path

    return svg_path("check-ink").as_posix()


def stylesheet(p: Palette) -> str:
    heading = f'"{HEADING_FAMILY}", "{FONT_FAMILY}", sans-serif'
    lime_hover, lime_press = mix(p.lime, "#000000", 0.06), mix(p.lime, "#000000", 0.12)
    quiet_hover, quiet_press = p.shade(p.bg, 0.06), p.shade(p.bg, 0.12)
    return f"""
    * {{ font-family: "{FONT_FAMILY}", -apple-system, "Segoe UI", sans-serif; font-size: 14px; }}
    QMainWindow, QWidget#root, QScrollArea, QScrollArea > QWidget > QWidget {{ background: {p.bg}; }}
    QWidget {{ color: {p.text}; selection-background-color: {p.lime}; selection-color: {p.on_accent}; }}
    QWidget#topbar, QWidget#footer {{ background: {p.bg}; }}
    QWidget#footer {{ border-top: 1px solid {p.line}; }}

    QLabel {{ background: transparent; }}
    QLabel[role="brand"] {{ font-family: {heading}; font-size: 18px; font-weight: 700; letter-spacing: -0.3px; }}
    QLabel[role="title"] {{ font-family: {heading}; font-size: 30px; font-weight: 700; letter-spacing: -0.6px; }}
    QLabel[role="subtitle"] {{ font-size: 15px; color: {p.text_muted}; }}
    QLabel[role="heading"] {{ font-family: {heading}; font-size: 17px; font-weight: 600; }}
    QLabel[role="error-title"] {{ font-family: {heading}; font-size: 20px; font-weight: 600; color: {p.rose}; }}
    QLabel[role="lead"] {{ font-size: 15px; }}
    QLabel[role="muted"] {{ color: {p.text_muted}; }}
    QLabel[role="caption"] {{ font-size: 12px; color: {p.text_muted}; }}
    QLabel[role="mono"] {{ font-family: {MONO_FAMILY}; font-size: 13px; }}
    QLabel[role="stat"] {{ font-family: {heading}; font-size: 36px; font-weight: 700; letter-spacing: -0.6px; color: {p.on_accent}; }}
    QLabel[role="stat-label"] {{ font-size: 13px; color: {p.on_accent}; }}
    QLabel[role="percent"] {{ font-family: {heading}; font-size: 36px; font-weight: 700; letter-spacing: -0.6px; }}
    QLabel[role="state"] {{ font-size: 13px; font-weight: 600; }}

    QFrame[surface="true"] {{ background: {p.panel}; border: 1px solid {p.line}; border-radius: {TILE_RADIUS}px; }}
    QFrame[surface="true"] QLabel {{ border: none; }}
    QFrame[surface="true"][tone="error"] {{ border-color: {p.rose}; }}
    QFrame[warn="true"] {{ background: {p.warn}; border: none; border-radius: 10px; }}
    QFrame[warn="true"] QLabel {{ color: {p.text}; border: none; }}
    QFrame[divider="true"] {{ background: {p.line}; border: none; min-height: 1px; max-height: 1px; }}

    QPushButton {{
        background: transparent; color: {p.text}; border: 1px solid {p.line_strong()}; border-radius: 8px;
        padding: 9px 18px; font-weight: 600; min-height: 20px;
    }}
    QPushButton:hover {{ background: {quiet_hover}; }}
    QPushButton:pressed {{ background: {quiet_press}; }}
    QPushButton:disabled {{ color: {p.text_muted}; border-color: {p.line}; background: transparent; }}
    QPushButton:focus {{ border: 2px solid {p.text}; padding: 8px 17px; outline: none; }}
    QPushButton[variant="primary"] {{ background: {p.lime}; color: {p.on_accent}; border: 1px solid {p.lime}; }}
    QPushButton[variant="primary"]:hover {{ background: {lime_hover}; border-color: {lime_hover}; }}
    QPushButton[variant="primary"]:pressed {{ background: {lime_press}; border-color: {lime_press}; }}
    QPushButton[variant="primary"]:focus {{ border: 2px solid {p.on_accent}; }}
    QPushButton[variant="primary"]:disabled {{ background: {p.warn}; color: {p.text_muted}; border-color: {p.warn}; }}
    QPushButton[variant="danger"] {{ color: {p.text}; border: 1px solid {p.rose}; }}
    QPushButton[variant="danger"]:focus {{ border: 2px solid {p.rose}; }}
    QPushButton[variant="danger"]:disabled {{ color: {p.text_muted}; border-color: {rgba(p.rose, 0.4)}; }}
    QPushButton[variant="text"] {{ border: 1px solid transparent; padding: 6px 8px; color: {p.text_muted}; min-height: 18px; }}
    QPushButton[variant="text"]:hover {{ color: {p.text}; background: {quiet_hover}; }}
    QPushButton[variant="text"]:checked {{ color: {p.text}; border-bottom: 2px solid {p.lime}; border-radius: 0; }}
    QPushButton[variant="text"]:focus {{ border: 2px solid {p.text}; padding: 5px 7px; }}
    QPushButton[variant="text"]:checked:focus {{ border-radius: 8px; }}

    QLineEdit {{ background: {p.panel}; border: 1px solid {p.line}; border-radius: 8px; padding: 8px 10px; }}
    QLineEdit:focus {{ border: 2px solid {p.lime}; padding: 7px 9px; background: {p.warn}; }}
    QLineEdit[role="key"] {{ font-family: {MONO_FAMILY}; font-size: 18px; font-weight: 500; padding: 10px 0; }}
    QLineEdit[role="key"]:focus {{ border: 2px solid {p.lime}; padding: 9px 0; background: {p.warn}; }}
    QLineEdit[role="key"]:disabled {{ color: {p.text_muted}; }}
    QLineEdit[role="key"][invalid="true"] {{ border: 2px solid {p.rose}; padding: 9px 0; background: {p.panel}; }}

    QCheckBox {{ spacing: 12px; }}
    QCheckBox::indicator {{ width: 20px; height: 20px; border-radius: 5px; border: 1.5px solid {p.text_muted}; background: {p.panel}; }}
    QCheckBox::indicator:hover {{ border-color: {p.text}; }}
    QCheckBox::indicator:checked {{ background: {p.lime}; border-color: {p.lime}; image: url({_check_url()}); }}
    QCheckBox:focus {{ outline: none; }}
    QCheckBox[focused="true"]::indicator {{ border: 2px solid {p.text}; }}
    QCheckBox[focused="true"]::indicator:checked {{ border: 2px solid {p.text}; }}

    QScrollArea {{ border: none; }}
    QScrollBar:vertical {{ background: transparent; width: 10px; margin: 2px; }}
    QScrollBar::handle:vertical {{ background: {p.line_strong()}; border-radius: 4px; min-height: 30px; }}
    QScrollBar::handle:vertical:hover {{ background: {p.text_muted}; }}
    QScrollBar::add-line, QScrollBar::sub-line, QScrollBar::add-page, QScrollBar::sub-page {{ background: none; height: 0; }}

    QToolTip {{ background: {p.text}; color: {p.bg}; border: none; padding: 6px 8px; border-radius: 6px; font-size: 13px; }}
    QDialog {{ background: {p.bg}; }}
    QMessageBox QLabel {{ font-size: 14px; }}
    """


def apply(app: QApplication, dark: bool) -> Palette:
    global _current
    _current = palette(dark)
    p = _current
    qp = QPalette()
    qp.setColor(QPalette.ColorRole.Window, QColor(p.bg))
    qp.setColor(QPalette.ColorRole.Base, QColor(p.panel))
    qp.setColor(QPalette.ColorRole.AlternateBase, QColor(p.bg))
    qp.setColor(QPalette.ColorRole.Text, QColor(p.text))
    qp.setColor(QPalette.ColorRole.WindowText, QColor(p.text))
    qp.setColor(QPalette.ColorRole.ButtonText, QColor(p.text))
    qp.setColor(QPalette.ColorRole.Button, QColor(p.panel))
    qp.setColor(QPalette.ColorRole.Highlight, QColor(p.lime))
    qp.setColor(QPalette.ColorRole.HighlightedText, QColor(p.on_accent))
    qp.setColor(QPalette.ColorRole.PlaceholderText, QColor(p.text_muted))
    qp.setColor(QPalette.ColorRole.ToolTipBase, QColor(p.text))
    qp.setColor(QPalette.ColorRole.ToolTipText, QColor(p.bg))
    app.setPalette(qp)
    app.setStyleSheet(stylesheet(p))
    app.setProperty("chatport_dark", dark)
    return p


def repolish(widget) -> None:
    """Re-apply the stylesheet after a dynamic property changed."""
    style = widget.style()
    style.unpolish(widget)
    style.polish(widget)
    widget.update()
