"""Colors and the application stylesheet. One teal accent, a small hue palette for chips, light and dark."""
from __future__ import annotations

import os
from dataclasses import dataclass

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QGuiApplication, QPalette
from PySide6.QtWidgets import QApplication

FONT_FAMILY = "Inter"
MONO_FAMILY = '"SF Mono", Menlo, Consolas, "DejaVu Sans Mono", monospace'
RAIL_WIDTH = 240
CARD_RADIUS = 14

# Which hue a given icon gets in a chip. Anything not listed falls back to the accent.
ICON_HUES = {
    "phone-android": "teal", "phone-iphone": "blue", "laptop": "violet", "key": "amber",
    "alert": "amber", "x": "rose", "trash": "rose", "undo": "amber", "check": "teal",
    "shield": "blue", "arrow-right": "teal", "info": "blue", "lock": "teal", "download": "blue",
}


@dataclass(frozen=True)
class Palette:
    bg: str
    surface: str
    surface2: str
    border: str
    text: str
    text_muted: str
    accent: str
    accent_text: str
    blue: str
    amber: str
    rose: str
    violet: str
    shadow_alpha: int
    dark: bool = False

    # Semantic names that older call sites and `getattr(palette, key)` lookups rely on.
    @property
    def danger(self) -> str:
        return self.rose

    @property
    def warning(self) -> str:
        return self.amber

    @property
    def success(self) -> str:
        return self.accent

    @property
    def teal(self) -> str:
        return self.accent

    @property
    def accent_soft(self) -> str:
        return mix(self.accent, self.surface, 0.86)

    @property
    def surface_hover(self) -> str:
        return self.surface2

    @property
    def rail(self) -> str:
        return "#121820" if self.dark else "#EEF1F4"

    @property
    def chip_alpha(self) -> float:
        return 0.16 if self.dark else 0.12

    def hue(self, name: str) -> str:
        """A palette color by hue name (teal, blue, amber, rose, violet, muted) or attribute name."""
        if name in ("teal", "accent", "success", "green"):
            return self.accent
        if name in ("muted", "gray", "text_muted", "checking"):
            return self.text_muted
        return getattr(self, name, self.accent)

    def tint(self, name: str, alpha: float | None = None) -> str:
        """The hue at low alpha, as a stylesheet color."""
        return rgba(self.hue(name), self.chip_alpha if alpha is None else alpha)

    def shadow(self) -> QColor:
        color = QColor("#0B1B2B" if not self.dark else "#000000")
        color.setAlpha(self.shadow_alpha)
        return color


LIGHT = Palette(
    bg="#F6F8FA", surface="#FFFFFF", surface2="#F0F3F6", border="rgba(16, 32, 48, 0.10)",
    text="#15202B", text_muted="#5F6C7B",
    accent="#1FA37A", accent_text="#FFFFFF",
    blue="#2F6FEB", amber="#D98B1F", rose="#D94F6B", violet="#7C5CE6",
    shadow_alpha=46,
)
DARK = Palette(
    bg="#0F1419", surface="#171D24", surface2="#1F2730", border="rgba(255, 255, 255, 0.08)",
    text="#E7ECF1", text_muted="#95A2B1",
    accent="#2FC08F", accent_text="#07130E",
    blue="#6B9BFF", amber="#F0B04A", rose="#F27389", violet="#A48CFF",
    shadow_alpha=115, dark=True,
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


_mix = mix


def stylesheet(p: Palette) -> str:
    top = mix(p.accent, "#FFFFFF", 0.14)
    hover_top, hover_bottom = mix(p.accent, "#FFFFFF", 0.24), mix(p.accent, "#FFFFFF", 0.08)
    press_top, press_bottom = mix(p.accent, "#000000", 0.06), mix(p.accent, "#000000", 0.16)
    primary = f"qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 {top}, stop:1 {p.accent})"
    primary_hover = f"qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 {hover_top}, stop:1 {hover_bottom})"
    primary_press = f"qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 {press_top}, stop:1 {press_bottom})"
    chunk = f"qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 {mix(p.accent, '#FFFFFF', 0.18)}, stop:1 {p.accent})"
    track = p.surface2 if not p.dark else mix(p.surface2, "#FFFFFF", 0.06)
    return f"""
    * {{ font-family: "{FONT_FAMILY}", -apple-system, "Segoe UI", sans-serif; font-size: 14px; }}
    QMainWindow, QWidget#root, QScrollArea, QScrollArea > QWidget > QWidget {{ background: {p.bg}; }}
    QWidget {{ color: {p.text}; selection-background-color: {p.accent}; selection-color: {p.accent_text}; }}
    QWidget#rail {{ background: {p.rail}; border-right: 1px solid {p.border}; }}
    QWidget#header, QWidget#footer {{ background: {p.bg}; }}
    QWidget#footer {{ border-top: 1px solid {p.border}; }}
    QFrame#controls {{ background: {p.surface2}; border: 1px solid {p.border}; border-radius: 10px; }}
    QFrame#controls QFrame#divider {{ background: {p.border}; border: none; max-width: 1px; min-width: 1px; }}

    QLabel {{ background: transparent; }}
    QLabel[role="title"] {{ font-size: 28px; font-weight: 600; letter-spacing: -0.5px; }}
    QLabel[role="subtitle"] {{ font-size: 15px; color: {p.text_muted}; }}
    QLabel[role="muted"] {{ font-size: 14px; color: {p.text_muted}; }}
    QLabel[role="caption"] {{ font-size: 12px; color: {p.text_muted}; }}
    QLabel[role="eyebrow"] {{ font-size: 12px; font-weight: 600; color: {p.accent}; letter-spacing: 1px; }}
    QLabel[role="heading"] {{ font-size: 16px; font-weight: 600; }}
    QLabel[role="mono"] {{ font-family: {MONO_FAMILY}; font-size: 13px; }}
    QLabel[role="danger"] {{ color: {p.rose}; }}
    QLabel[role="stat"] {{ font-size: 24px; font-weight: 600; letter-spacing: -0.3px; }}
    QLabel[role="percent"] {{ font-size: 28px; font-weight: 600; letter-spacing: -0.5px; }}

    QFrame[card="true"] {{ background: {p.surface}; border: 1px solid {p.border}; border-radius: {CARD_RADIUS}px; }}
    QFrame[card="true"][nested="true"] {{ background: {p.surface2}; border: 1px solid transparent; border-radius: 12px; }}
    QFrame[card="true"][tone="danger"] {{ border-color: {rgba(p.rose, 0.35)}; }}
    QFrame[card="true"][tone="accent"] {{ background: {p.tint("teal", 0.10)}; border-color: {rgba(p.accent, 0.28)}; }}
    QFrame[card="true"][tone="hero"] {{
        background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 {p.tint("teal", 0.14)}, stop:1 {p.tint("teal", 0.06)});
        border: 1px solid {rgba(p.accent, 0.18)}; border-radius: 18px;
    }}
    QFrame[card="true"][nested="true"][band="true"] {{ background: {p.surface}; border: 1px solid {p.border}; }}
    QFrame[card="true"] QLabel {{ background: transparent; border: none; }}
    QFrame[card="true"] QLabel[infochip="true"], QLabel[infochip="true"] {{
        background: {p.surface2}; color: {p.text_muted}; border: 1px solid {p.border};
        border-radius: 11px; padding: 2px 10px; font-size: 12px; font-weight: 600;
    }}
    QFrame#errorbar {{ background: {p.rose}; border: none; border-radius: 2px; min-width: 4px; max-width: 4px; }}
    QFrame[divider="true"] {{ background: {p.border}; border: none; min-height: 1px; max-height: 1px; }}

    QPushButton {{
        background: {p.surface}; color: {p.text}; border: 1px solid {p.border}; border-radius: 10px;
        padding: 9px 18px; font-weight: 600; min-height: 20px;
    }}
    QPushButton:hover {{ background: {p.surface2}; }}
    QPushButton:pressed {{ background: {mix(p.surface2, p.text, 0.08)}; }}
    QPushButton:disabled {{ color: {p.text_muted}; background: {p.bg}; border-color: {p.border}; }}
    QPushButton:focus {{ border-color: {p.accent}; outline: none; }}
    QPushButton[variant="primary"] {{ background: {primary}; color: {p.accent_text}; border: 1px solid {mix(p.accent, '#000000', 0.12)}; }}
    QPushButton[variant="primary"]:hover {{ background: {primary_hover}; }}
    QPushButton[variant="primary"]:pressed {{ background: {primary_press}; }}
    QPushButton[variant="primary"]:disabled {{ background: {rgba(p.accent, 0.40)}; color: {rgba(p.accent_text, 0.75)}; border-color: transparent; }}
    QPushButton[variant="quiet"] {{ background: transparent; border-color: transparent; color: {p.text_muted}; }}
    QPushButton[variant="quiet"]:hover {{ background: {p.surface2}; color: {p.text}; }}
    QPushButton[variant="quiet"]:disabled {{ background: transparent; color: {rgba(p.text_muted, 0.6)}; }}
    QPushButton[variant="danger"] {{ color: {p.rose}; border-color: {rgba(p.rose, 0.45)}; background: {p.surface}; }}
    QPushButton[variant="danger"]:hover {{ background: {rgba(p.rose, 0.12)}; }}
    QPushButton[variant="danger"]:pressed {{ background: {rgba(p.rose, 0.22)}; }}
    QPushButton[variant="danger"]:disabled {{ color: {rgba(p.rose, 0.45)}; border-color: {rgba(p.rose, 0.2)}; background: transparent; }}
    QPushButton[variant="icon"] {{ background: transparent; border-color: transparent; padding: 5px; border-radius: 8px; min-height: 18px; }}
    QPushButton[variant="icon"]:hover {{ background: {p.surface}; }}
    QPushButton[variant="seg"] {{ background: transparent; border-color: transparent; padding: 4px 10px; color: {p.text_muted}; font-size: 12px; font-weight: 600; border-radius: 7px; min-height: 18px; }}
    QPushButton[variant="seg"]:hover {{ color: {p.text}; }}
    QPushButton[variant="seg"]:checked {{ background: {p.surface}; color: {p.text}; border-color: {p.border}; }}

    QLineEdit {{
        background: {p.surface}; border: 1px solid {p.border}; border-radius: 10px; padding: 8px 10px;
        selection-background-color: {p.accent};
    }}
    QLineEdit:focus {{ border: 2px solid {p.accent}; padding: 7px 9px; }}
    QLineEdit[role="key"] {{ font-family: {MONO_FAMILY}; font-size: 18px; font-weight: 500; padding: 10px 0; background: {p.surface2}; border: 1px solid transparent; }}
    QLineEdit[role="key"]:hover {{ border-color: {p.border}; }}
    QLineEdit[role="key"]:focus {{ border: 2px solid {p.accent}; padding: 9px 0; background: {p.surface}; }}
    QLineEdit[role="key"]:disabled {{ color: {p.text_muted}; }}
    QLineEdit[role="key"][invalid="true"] {{ border: 2px solid {p.rose}; padding: 9px 0; background: {rgba(p.rose, 0.08)}; }}
    QLineEdit[invalid="true"] {{ border-color: {p.rose}; }}

    QProgressBar {{ background: {track}; border: none; border-radius: 5px; min-height: 10px; max-height: 10px; text-align: center; color: transparent; }}
    QProgressBar::chunk {{ background: {chunk}; border-radius: 5px; }}

    QCheckBox {{ spacing: 10px; }}
    QCheckBox::indicator {{ width: 20px; height: 20px; border-radius: 6px; border: 1.5px solid {rgba(p.text_muted, 0.7)}; background: {p.surface}; }}
    QCheckBox::indicator:hover {{ border-color: {p.accent}; }}
    QCheckBox::indicator:checked {{ background: {p.accent}; border-color: {p.accent}; image: url({_check_url()}); }}

    QScrollArea {{ border: none; }}
    QScrollBar:vertical {{ background: transparent; width: 10px; margin: 2px; }}
    QScrollBar::handle:vertical {{ background: {rgba(p.text_muted, 0.35)}; border-radius: 4px; min-height: 30px; }}
    QScrollBar::handle:vertical:hover {{ background: {p.text_muted}; }}
    QScrollBar::add-line, QScrollBar::sub-line, QScrollBar::add-page, QScrollBar::sub-page {{ background: none; height: 0; }}

    QToolTip {{ background: {p.text}; color: {p.bg}; border: none; padding: 6px 8px; border-radius: 6px; font-size: 13px; }}
    QDialog {{ background: {p.bg}; }}
    QMessageBox QLabel {{ font-size: 14px; }}
    """


def _check_url() -> str:
    from .icons import svg_path

    return svg_path("check-white").as_posix()


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
