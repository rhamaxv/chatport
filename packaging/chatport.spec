# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller spec for Chatport. One-folder bundle; macOS additionally gets a .app.

Build from the repository root:
    python -m PyInstaller --noconfirm --clean packaging/chatport.spec
Run packaging/make_icons.py first so packaging/out/Chatport.{icns,ico} exist.
"""
import sys
import tomllib
from pathlib import Path

from PyInstaller.utils.hooks import collect_all, collect_submodules

ROOT = Path(SPECPATH).resolve().parent  # noqa: F821  SPECPATH is injected by PyInstaller
SRC = ROOT / "src"
OUT = ROOT / "packaging" / "out"

with open(ROOT / "pyproject.toml", "rb") as fh:
    VERSION = tomllib.load(fh)["project"]["version"]

if sys.platform == "darwin":
    ICON = str(OUT / "Chatport.icns")
elif sys.platform == "win32":
    ICON = str(OUT / "Chatport.ico")
else:
    ICON = None

datas = [
    (str(SRC / "chatport" / "ui" / "assets"), "chatport/ui/assets"),
    (str(SRC / "chatport" / "i18n"), "chatport/i18n"),
]
binaries = []
hiddenimports = []

# pymobiledevice3 loads plugins and data files dynamically; take everything.
pmd_datas, pmd_binaries, pmd_hidden = collect_all("pymobiledevice3")
datas += pmd_datas
binaries += pmd_binaries
hiddenimports += pmd_hidden

hiddenimports += collect_submodules("wamove")
hiddenimports += collect_submodules("chatport")

a = Analysis(
    [str(ROOT / "packaging" / "launch.py")],
    pathex=[str(SRC)],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=["tkinter", "matplotlib", "numpy", "IPython", "pytest"],
    noarchive=False,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="Chatport",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=ICON,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    name="Chatport",
)

if sys.platform == "darwin":
    app = BUNDLE(
        coll,
        name="Chatport.app",
        icon=ICON,
        bundle_identifier="io.github.rhamaxv.chatport",
        info_plist={
            "CFBundleName": "Chatport",
            "CFBundleDisplayName": "Chatport",
            "CFBundleShortVersionString": VERSION,
            "CFBundleVersion": VERSION,
            "LSMinimumSystemVersion": "12.0",
            "NSHighResolutionCapable": True,
            "LSApplicationCategoryType": "public.app-category.utilities",
            "NSHumanReadableCopyright": "GPL-3.0-or-later",
        },
    )
