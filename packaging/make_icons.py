"""Render packaging/icon.svg to every size Chatport ships.

Outputs, all under packaging/out/:
  icon-<size>.png for 16, 32, 64, 128, 256, 512, 1024
  icon-mono-256.png (preview of icon-mono.svg)
  Chatport.ico (16..256, via Pillow)
  Chatport.icns (macOS only, via iconutil)

Also copies icon-256.png to src/chatport/ui/assets/app-icon.png, but only
when that file does not exist yet, so a hand-tuned asset is never overwritten.

Run with the project venv: python packaging/make_icons.py
"""
from __future__ import annotations

import os
import platform
import shutil
import subprocess
import sys
from pathlib import Path

# Must be set before any Qt import so no display is needed (CI, ssh, build boxes).
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QRectF, Qt  # noqa: E402
from PySide6.QtGui import QGuiApplication, QImage, QPainter  # noqa: E402
from PySide6.QtSvg import QSvgRenderer  # noqa: E402

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
OUT = HERE / "out"
ICON_SVG = HERE / "icon.svg"
MONO_SVG = HERE / "icon-mono.svg"
APP_ICON_TARGET = ROOT / "src" / "chatport" / "ui" / "assets" / "app-icon.png"

PNG_SIZES = (16, 32, 64, 128, 256, 512, 1024)
ICO_SIZES = (16, 32, 48, 64, 128, 256)
# iconutil wants these exact names inside the .iconset folder.
ICONSET = (
    ("icon_16x16.png", 16),
    ("icon_16x16@2x.png", 32),
    ("icon_32x32.png", 32),
    ("icon_32x32@2x.png", 64),
    ("icon_128x128.png", 128),
    ("icon_128x128@2x.png", 256),
    ("icon_256x256.png", 256),
    ("icon_256x256@2x.png", 512),
    ("icon_512x512.png", 512),
    ("icon_512x512@2x.png", 1024),
)


def render_svg(svg: Path, size: int) -> QImage:
    renderer = QSvgRenderer(str(svg))
    if not renderer.isValid():
        raise SystemExit(f"invalid SVG: {svg}")
    image = QImage(size, size, QImage.Format.Format_ARGB32_Premultiplied)
    image.fill(Qt.GlobalColor.transparent)
    painter = QPainter(image)
    painter.setRenderHints(
        QPainter.RenderHint.Antialiasing
        | QPainter.RenderHint.SmoothPixmapTransform
        | QPainter.RenderHint.TextAntialiasing
    )
    renderer.render(painter, QRectF(0, 0, size, size))
    painter.end()
    return image


def save_png(image: QImage, path: Path) -> None:
    if not image.save(str(path), "PNG"):
        raise SystemExit(f"could not write {path}")


def build_ico(pngs: dict[int, Path], target: Path) -> None:
    from PIL import Image

    frames = [Image.open(pngs[s]).convert("RGBA") for s in ICO_SIZES if s in pngs]
    missing = [s for s in ICO_SIZES if s not in pngs]
    for s in missing:
        frames.append(Image.open(pngs[256]).convert("RGBA").resize((s, s), Image.LANCZOS))
    frames.sort(key=lambda im: im.width)
    base = frames[-1]
    base.save(
        target,
        format="ICO",
        sizes=[(im.width, im.height) for im in frames],
        append_images=frames[:-1],
    )


def build_icns(pngs: dict[int, Path], target: Path) -> bool:
    if platform.system() != "Darwin" or shutil.which("iconutil") is None:
        return False
    iconset = OUT / "Chatport.iconset"
    if iconset.exists():
        shutil.rmtree(iconset)
    iconset.mkdir()
    for name, size in ICONSET:
        shutil.copyfile(pngs[size], iconset / name)
    subprocess.run(["iconutil", "-c", "icns", str(iconset), "-o", str(target)], check=True)
    shutil.rmtree(iconset)
    return True


def main() -> int:
    app = QGuiApplication.instance() or QGuiApplication(sys.argv)  # noqa: F841 keeps Qt alive
    OUT.mkdir(parents=True, exist_ok=True)

    pngs: dict[int, Path] = {}
    for size in PNG_SIZES:
        path = OUT / f"icon-{size}.png"
        save_png(render_svg(ICON_SVG, size), path)
        pngs[size] = path
        print(f"wrote {path.relative_to(ROOT)}")
    for size in ICO_SIZES:
        if size not in pngs:
            path = OUT / f"icon-{size}.png"
            save_png(render_svg(ICON_SVG, size), path)
            pngs[size] = path
            print(f"wrote {path.relative_to(ROOT)}")

    mono = OUT / "icon-mono-256.png"
    save_png(render_svg(MONO_SVG, 256), mono)
    print(f"wrote {mono.relative_to(ROOT)}")

    ico = OUT / "Chatport.ico"
    build_ico(pngs, ico)
    print(f"wrote {ico.relative_to(ROOT)}")

    icns = OUT / "Chatport.icns"
    if build_icns(pngs, icns):
        print(f"wrote {icns.relative_to(ROOT)}")
    else:
        print("skipped Chatport.icns (needs macOS with iconutil)")

    if APP_ICON_TARGET.exists():
        print(f"kept existing {APP_ICON_TARGET.relative_to(ROOT)}")
    else:
        APP_ICON_TARGET.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(pngs[256], APP_ICON_TARGET)
        print(f"wrote {APP_ICON_TARGET.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
