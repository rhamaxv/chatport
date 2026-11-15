"""Colors and the application stylesheet. One accent, neutral grays, light and dark."""
from __future__ import annotations

import os
from dataclasses import dataclass

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QGuiApplication, QPalette
from PySide6.QtWidgets import QApplication

FONT_FAMILY = "Inter"
RAIL_WIDTH = 240


@dataclass(frozen=True)
class Palette:
    bg: str
    surface: str
    border: str
    text: str
    text_muted: str
    accent: str
    accent_text: str
    danger: str
    warning: str
    success: str
    dark: bool = False

    @property
    def accent_soft(self) -> str:
        return "#17322A" if self.dark else "#E6F5EF"

    @property
    def surface_hover(self) -> str:
        return "#262B33" if self.dark else "#F1F3F5"

    @property
    def rail(self) -> str:
        return "#111417" if self.dark else "#EEF0F3"


LIGHT = Palette(
    bg="#F6F7F9", surface="#FFFFFF", border="#E2E5E9", text="#1A1D21", text_muted="#6B7280",
    accent="#1FA37A", accent_text="#FFFFFF", danger="#D64545", warning="#C9850A", success="#1FA37A",
)
DARK = Palette(
    bg="#15181C", surface="#1E2228", border="#2C323A", text="#E8EAED", text_muted="#9AA3AE",
    accent="#2FC08F", accent_text="#0E1A15", danger="#F26B6B", warning="#F0B429", success="#2FC08F",
    dark=True,
)

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


def stylesheet(p: Palette) -> str:
    return f"""
    * {{ font-family: "{FONT_FAMILY}", -apple-system, "Segoe UI", sans-serif; font-size: 16px; }}
    QMainWindow, QWidget#root, QScrollArea, QScrollArea > QWidget > QWidget {{ background: {p.bg}; }}
    QWidget {{ color: {p.text}; selection-background-color: {p.accent}; selection-color: {p.accent_text}; }}
    QWidget#rail {{ background: {p.rail}; border-right: 1px solid {p.border}; }}
    QWidget#header, QWidget#footer {{ background: {p.bg}; }}
    QWidget#footer {{ border-top: 1px solid {p.border}; }}

    QLabel {{ background: transparent; }}
    QLabel[role="title"] {{ font-size: 26px; font-weight: 600; letter-spacing: -0.3px; }}
    QLabel[role="subtitle"] {{ font-size: 16px; color: {p.text_muted}; }}
    QLabel[role="muted"] {{ font-size: 14px; color: {p.text_muted}; }}
    QLabel[role="heading"] {{ font-size: 16px; font-weight: 600; }}
    QLabel[role="mono"] {{ font-family: "SF Mono", Menlo, Consolas, monospace; font-size: 14px; }}
    QLabel[role="danger"] {{ color: {p.danger}; }}
    QLabel[role="stat"] {{ font-size: 22px; font-weight: 600; }}

    QFrame[card="true"] {{ background: {p.surface}; border: 1px solid {p.border}; border-radius: 12px; }}
    QFrame[card="true"][tone="danger"] {{ border-color: {_mix(p.danger, p.surface, 0.55)}; }}
    QFrame[card="true"][tone="accent"] {{ background: {p.accent_soft}; border-color: transparent; }}
    QFrame[card="true"] QLabel {{ background: transparent; border: none; }}

    QPushButton {{
        background: {p.surface}; color: {p.text}; border: 1px solid {p.border}; border-radius: 8px;
        padding: 9px 18px; font-weight: 500; min-height: 20px;
    }}
    QPushButton:hover {{ background: {p.surface_hover}; }}
    QPushButton:pressed {{ background: {p.border}; }}
    QPushButton:disabled {{ color: {p.text_muted}; background: {p.bg}; border-color: {p.border}; }}
    QPushButton:focus {{ border-color: {p.accent}; outline: none; }}
    QPushButton[variant="primary"] {{ background: {p.accent}; color: {p.accent_text}; border-color: {p.accent}; }}
    QPushButton[variant="primary"]:hover {{ background: {_mix(p.accent, p.text, 0.12)}; }}
    QPushButton[variant="primary"]:disabled {{ background: {_mix(p.accent, p.bg, 0.6)}; color: {_mix(p.accent_text, p.bg, 0.4)}; border-color: transparent; }}
    QPushButton[variant="quiet"] {{ background: transparent; border-color: transparent; color: {p.text_muted}; }}
    QPushButton[variant="quiet"]:hover {{ background: {p.surface_hover}; color: {p.text}; }}
    QPushButton[variant="danger"] {{ color: {p.danger}; border-color: {_mix(p.danger, p.surface, 0.5)}; }}
    QPushButton[variant="danger"]:hover {{ background: {_mix(p.danger, p.surface, 0.9)}; }}
    QPushButton[variant="icon"] {{ background: transparent; border-color: transparent; padding: 6px; border-radius: 8px; }}
    QPushButton[variant="icon"]:hover {{ background: {p.surface_hover}; }}
    QPushButton[variant="seg"] {{ background: transparent; border-color: transparent; padding: 4px 10px; color: {p.text_muted}; font-size: 13px; font-weight: 600; border-radius: 6px; }}
    QPushButton[variant="seg"]:checked {{ background: {p.surface}; color: {p.text}; border-color: {p.border}; }}

    QLineEdit {{
        background: {p.surface}; border: 1px solid {p.border}; border-radius: 8px; padding: 8px 10px;
        selection-background-color: {p.accent};
    }}
    QLineEdit:focus {{ border: 2px solid {p.accent}; padding: 7px 9px; }}
    QLineEdit[role="key"] {{ font-family: "SF Mono", Menlo, Consolas, monospace; font-size: 18px; font-weight: 500; padding: 10px 0; }}
    QLineEdit[invalid="true"] {{ border-color: {p.danger}; }}

    QProgressBar {{ background: {p.border}; border: none; border-radius: 4px; min-height: 8px; max-height: 8px; text-align: center; color: transparent; }}
    QProgressBar::chunk {{ background: {p.accent}; border-radius: 4px; }}

    QCheckBox {{ spacing: 10px; }}
    QCheckBox::indicator {{ width: 20px; height: 20px; border-radius: 6px; border: 1.5px solid {p.text_muted}; background: {p.surface}; }}
    QCheckBox::indicator:hover {{ border-color: {p.accent}; }}
    QCheckBox::indicator:checked {{ background: {p.accent}; border-color: {p.accent}; image: url({_check_url()}); }}

    QScrollArea {{ border: none; }}
    QScrollBar:vertical {{ background: transparent; width: 10px; margin: 2px; }}
    QScrollBar::handle:vertical {{ background: {p.border}; border-radius: 5px; min-height: 30px; }}
    QScrollBar::handle:vertical:hover {{ background: {p.text_muted}; }}
    QScrollBar::add-line, QScrollBar::sub-line, QScrollBar::add-page, QScrollBar::sub-page {{ background: none; height: 0; }}

    QToolTip {{ background: {p.text}; color: {p.bg}; border: none; padding: 6px 8px; border-radius: 6px; font-size: 13px; }}
    QDialog {{ background: {p.bg}; }}
    QMessageBox QLabel {{ font-size: 15px; }}
    """


def _check_url() -> str:
    from .icons import svg_path

    return svg_path("check-white").as_posix()


def _mix(a: str, b: str, amount: float) -> str:
    """Blend color a toward color b by amount (0..1)."""
    ca, cb = QColor(a), QColor(b)
    r = round(ca.red() + (cb.red() - ca.red()) * amount)
    g = round(ca.green() + (cb.green() - ca.green()) * amount)
    bl = round(ca.blue() + (cb.blue() - ca.blue()) * amount)
    return QColor(r, g, bl).name()


def apply(app: QApplication, dark: bool) -> Palette:
    global _current
    _current = palette(dark)
    p = _current
    qp = QPalette()
    qp.setColor(QPalette.ColorRole.Window, QColor(p.bg))
    qp.setColor(QPalette.ColorRole.Base, QColor(p.surface))
    qp.setColor(QPalette.ColorRole.AlternateBase, QColor(p.bg))
    qp.setColor(QPalette.ColorRole.Text, QColor(p.text))
    qp.setColor(QPalette.ColorRole.WindowText, QColor(p.text))
    qp.setColor(QPalette.ColorRole.ButtonText, QColor(p.text))
    qp.setColor(QPalette.ColorRole.Button, QColor(p.surface))
    qp.setColor(QPalette.ColorRole.Highlight, QColor(p.accent))
    qp.setColor(QPalette.ColorRole.HighlightedText, QColor(p.accent_text))
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
