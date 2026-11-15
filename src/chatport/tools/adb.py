"""Locate, download and verify the Android platform-tools adb binary."""

from __future__ import annotations

import logging
import os
import re
import shutil
import stat
import subprocess
import sys
import tempfile
import zipfile
from collections.abc import Callable
from pathlib import Path

from chatport.tools.download import DownloadError, download_file

log = logging.getLogger("chatport.tools")

_REPO = "https://dl.google.com/android/repository/"
URLS = {
    "darwin": _REPO + "platform-tools-latest-darwin.zip",
    "win32": _REPO + "platform-tools-latest-windows.zip",
    "linux": _REPO + "platform-tools-latest-linux.zip",
}

PREFIX = "platform-tools/"
VERIFY_TIMEOUT = 30
_VERSION_RE = re.compile(r"Android Debug Bridge version\s+(\S+)")


class AdbDownloadError(Exception):
    """Download, extraction or verification of platform-tools failed."""


def _platform(platform: str | None = None) -> str:
    return platform or sys.platform


def binary_name(platform: str | None = None) -> str:
    return "adb.exe" if _platform(platform).startswith("win") else "adb"


def bundled(adb_dir: Path, platform: str | None = None) -> Path:
    return Path(adb_dir) / "platform-tools" / binary_name(platform)


WINDOWS_EXECUTABLE_SUFFIXES = (".exe", ".cmd", ".bat", ".com")


def _common_locations(platform: str) -> list[str]:
    """Well known install paths. POSIX paths stay literal strings so they never get backslashes."""
    if platform.startswith("win"):
        local = os.environ.get("LOCALAPPDATA", "")
        program_data = os.environ.get("ProgramData", r"C:\ProgramData")
        locations = []
        if local:
            locations.append(os.path.join(local, "Android", "Sdk", "platform-tools", "adb.exe"))
        locations.append(
            os.path.join(program_data, "chocolatey", "lib", "adb", "tools", "platform-tools", "adb.exe")
        )
        return locations
    if platform == "darwin":
        return ["/opt/homebrew/bin/adb", os.path.expanduser("~/Library/Android/sdk/platform-tools/adb")]
    return ["/usr/bin/adb", os.path.expanduser("~/Android/Sdk/platform-tools/adb")]


def _executable(path: str | Path) -> bool:
    """Windows has no exec bit and os.access(X_OK) is true for any file, so go by suffix there."""
    if not os.path.isfile(path):
        return False
    if os.name == "nt":
        return str(path).lower().endswith(WINDOWS_EXECUTABLE_SUFFIXES)
    return os.access(path, os.X_OK)


def find(
    adb_dir: Path,
    platform: str | None = None,
    which: Callable[[str], str | None] = shutil.which,
) -> str | None:
    """Bundled copy first, then PATH, then well known SDK locations."""
    plat = _platform(platform)
    candidate = bundled(adb_dir, plat)
    if _executable(candidate):
        return str(candidate)
    on_path = which("adb")
    if on_path:
        return on_path
    for location in _common_locations(plat):
        if _executable(location):
            return location
    return None


def _safe_member(name: str) -> bool:
    if not name.startswith(PREFIX):
        return False
    normalized = name.replace("\\", "/")
    parts = normalized.split("/")
    return ".." not in parts and not normalized.startswith("/")


def _extract(archive: Path, dest: Path) -> None:
    dest_root = dest.resolve()
    with zipfile.ZipFile(archive) as zf:
        for info in zf.infolist():
            if not _safe_member(info.filename):
                log.debug("skipping zip member %s", info.filename)
                continue
            out = (dest / info.filename).resolve()
            if out != dest_root and dest_root not in out.parents:
                raise AdbDownloadError(f"unsafe zip member: {info.filename}")
            if info.is_dir():
                out.mkdir(parents=True, exist_ok=True)
                continue
            out.parent.mkdir(parents=True, exist_ok=True)
            with zf.open(info) as src, out.open("wb") as dst:
                shutil.copyfileobj(src, dst)
            mode = (info.external_attr >> 16) & 0o7777
            if mode and os.name != "nt":
                os.chmod(out, mode)


def download(
    adb_dir: Path,
    on_progress: Callable[[int, int], None],
    platform: str | None = None,
) -> str:
    """Fetch platform-tools into ``adb_dir`` and return the verified adb path."""
    plat = _platform(platform)
    url = URLS.get(plat) or URLS.get("linux" if plat.startswith("linux") else "")
    if not url:
        raise AdbDownloadError(f"no platform-tools build for {plat}")

    adb_dir = Path(adb_dir)
    adb_dir.mkdir(parents=True, exist_ok=True)
    final = adb_dir / "platform-tools"
    tmp = Path(tempfile.mkdtemp(prefix="platform-tools-", dir=adb_dir))
    try:
        archive = tmp / "platform-tools.zip"
        try:
            download_file(url, archive, on_progress)
        except DownloadError as exc:
            raise AdbDownloadError(str(exc)) from exc
        try:
            _extract(archive, tmp)
        except (zipfile.BadZipFile, OSError) as exc:
            raise AdbDownloadError(f"could not extract platform-tools: {exc}") from exc
        extracted = tmp / "platform-tools"
        exe = extracted / binary_name(plat)
        if not exe.is_file():
            raise AdbDownloadError("platform-tools archive has no adb binary")
        exe.chmod(exe.stat().st_mode | stat.S_IRWXU | stat.S_IRGRP | stat.S_IXGRP | stat.S_IROTH | stat.S_IXOTH)
        if version(str(exe)) is None:
            raise AdbDownloadError("downloaded adb does not run")
        if final.exists():
            shutil.rmtree(final, ignore_errors=True)
        extracted.rename(final)
    except AdbDownloadError:
        raise
    except Exception as exc:
        raise AdbDownloadError(f"adb download failed: {exc}") from exc
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    result = final / binary_name(plat)
    log.info("platform-tools ready at %s", result)
    return str(result)


def use(path: str) -> None:
    """Point the wamove engine at this adb binary."""
    import wamove.android.adb as wadb

    wadb._adb = lambda: path
    log.info("engine adb set to %s", path)


def version(path: str) -> str | None:
    """Return the version string reported by ``adb version`` or None if it does not run."""
    try:
        result = subprocess.run(
            [path, "version"],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=VERIFY_TIMEOUT,
        )
    except (OSError, subprocess.SubprocessError) as exc:
        log.debug("adb version failed: %s", exc)
        return None
    if result.returncode != 0:
        return None
    match = _VERSION_RE.search(result.stdout or "")
    return match.group(1) if match else None
