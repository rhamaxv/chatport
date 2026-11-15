#!/usr/bin/env bash
# macOS: PyInstaller bundle, ad-hoc signature, then Chatport-<version>.dmg in dist/.
# Usage: packaging/build.sh   (PYTHON=/path/to/python to pick an interpreter)
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
PY="${PYTHON:-python}"

VERSION="$("$PY" -c 'import tomllib,pathlib;print(tomllib.loads(pathlib.Path("pyproject.toml").read_text())["project"]["version"])')"
echo "Building Chatport $VERSION for macOS"

"$PY" packaging/make_icons.py
"$PY" -m PyInstaller --noconfirm --clean packaging/chatport.spec

APP="dist/Chatport.app"
[ -d "$APP" ] || { echo "missing $APP" >&2; exit 1; }

# Ad-hoc signature with the entitlements Python needs under the hardened runtime.
# Not notarized: users will see Gatekeeper and must use "Open Anyway" (documented in the README).
codesign --force --deep --sign - --options runtime \
    --entitlements packaging/entitlements.plist "$APP"
codesign --verify --deep --strict "$APP"

DMG="dist/Chatport-$VERSION.dmg"
STAGE="$(mktemp -d)"
trap 'rm -rf "$STAGE"' EXIT
cp -R "$APP" "$STAGE/"
ln -s /Applications "$STAGE/Applications"
rm -f "$DMG"
hdiutil create -volname "Chatport" -srcfolder "$STAGE" -ov -format UDZO "$DMG"

echo "Wrote $DMG"
