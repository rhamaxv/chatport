#!/usr/bin/env bash
# Linux: PyInstaller bundle, AppDir, then dist/Chatport-<version>-x86_64.AppImage.
# Usage: packaging/build-appimage.sh   (PYTHON=/path/to/python to pick an interpreter)
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
PY="${PYTHON:-python}"
ARCH="x86_64"
APPIMAGETOOL_URL="https://github.com/AppImage/appimagetool/releases/download/continuous/appimagetool-${ARCH}.AppImage"

VERSION="$("$PY" -c 'import tomllib,pathlib;print(tomllib.loads(pathlib.Path("pyproject.toml").read_text())["project"]["version"])')"
echo "Building Chatport $VERSION for Linux ($ARCH)"

"$PY" packaging/make_icons.py
"$PY" -m PyInstaller --noconfirm --clean packaging/chatport.spec
[ -x dist/Chatport/Chatport ] || { echo "missing dist/Chatport/Chatport" >&2; exit 1; }

APPDIR="build/AppDir"
rm -rf "$APPDIR"
mkdir -p "$APPDIR/usr/bin" "$APPDIR/usr/share/applications" "$APPDIR/usr/share/icons/hicolor/256x256/apps"
cp -a dist/Chatport/. "$APPDIR/usr/bin/"
cp packaging/chatport.desktop "$APPDIR/chatport.desktop"
cp packaging/chatport.desktop "$APPDIR/usr/share/applications/chatport.desktop"
cp packaging/out/icon-256.png "$APPDIR/chatport.png"
cp packaging/out/icon-256.png "$APPDIR/usr/share/icons/hicolor/256x256/apps/chatport.png"
ln -sf chatport.png "$APPDIR/.DirIcon"
ln -sf usr/bin/Chatport "$APPDIR/AppRun"

TOOL="build/appimagetool-${ARCH}.AppImage"
if [ ! -x "$TOOL" ]; then
    curl -fsSL -o "$TOOL" "$APPIMAGETOOL_URL"
    chmod +x "$TOOL"
fi

mkdir -p dist
OUTFILE="dist/Chatport-$VERSION-$ARCH.AppImage"
rm -f "$OUTFILE"
# --appimage-extract-and-run avoids needing FUSE on the build machine.
ARCH="$ARCH" "$TOOL" --appimage-extract-and-run --no-appstream "$APPDIR" "$OUTFILE"
chmod +x "$OUTFILE"

echo "Wrote $OUTFILE"
