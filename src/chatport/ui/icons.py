"""SVG line icons rendered in any color. The SVGs use currentColor; we recolor the rendered pixmap."""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from PySide6.QtCore import QRectF, Qt
from PySide6.QtGui import QColor, QIcon, QPainter, QPixmap
from PySide6.QtSvg import QSvgRenderer

ASSETS = Path(__file__).parent / "assets"
ICONS = ASSETS / "icons"
_SIZES = (16, 20, 24, 32, 48)


def svg_path(name: str) -> Path:
    return ICONS / f"{name}.svg"


@lru_cache(maxsize=512)
def _pixmap(name: str, size: int, color: str, dpr: float) -> QPixmap:
    px = int(round(size * dpr))
    pm = QPixmap(px, px)
    pm.fill(Qt.GlobalColor.transparent)
    path = svg_path(name)
    if path.is_file():
        renderer = QSvgRenderer(str(path))
        painter = QPainter(pm)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        renderer.render(painter, QRectF(0, 0, px, px))
        painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_SourceIn)
        painter.fillRect(pm.rect(), QColor(color))
        painter.end()
    pm.setDevicePixelRatio(dpr)
    return pm


def pixmap(name: str, size: int, color: str, dpr: float = 1.0) -> QPixmap:
    return _pixmap(name, size, color, float(dpr))


def icon(name: str, color: str) -> QIcon:
    result = QIcon()
    for size in _SIZES:
        result.addPixmap(pixmap(name, size, color, 1.0))
        result.addPixmap(pixmap(name, size, color, 2.0))
    return result


def available() -> list[str]:
    return sorted(p.stem for p in ICONS.glob("*.svg"))
