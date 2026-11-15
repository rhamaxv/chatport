"""Host OS checks for the iPhone side: usbmuxd on Linux, Apple's service on Windows."""

from __future__ import annotations

import logging
import os
import shutil
import subprocess
import sys
from pathlib import Path

log = logging.getLogger("chatport.tools")

APPLE_SERVICE = "Apple Mobile Device Service"
USBMUXD_SOCKET = Path("/var/run/usbmuxd")
OS_RELEASE = Path("/etc/os-release")
SC_TIMEOUT = 10

# Monkeypatchable seams for tests. Real callers never touch these.
which = shutil.which
run = subprocess.run
exists = Path.exists


def os_name(platform: str | None = None) -> str:
    plat = platform or sys.platform
    if plat == "darwin":
        return "macos"
    if plat.startswith("win") or plat == "cygwin":
        return "windows"
    return "linux"


def check(platform: str | None = None) -> dict:
    name = os_name(platform)
    if name == "macos":
        return {"state": "ok", "detail": "", "os": name}
    if name == "windows":
        return _check_windows(name)
    return _check_linux(name)


def _check_windows(name: str) -> dict:
    running = _apple_service_running()
    if running is None:
        installed = exists(_apple_support_dir())
        if installed:
            return {"state": "ok", "detail": "mobile device support installed", "os": name}
        return {"state": "apple_service_missing", "detail": "mobile device support not found", "os": name}
    if running:
        return {"state": "ok", "detail": "", "os": name}
    return {"state": "apple_service_missing", "detail": "service not running", "os": name}


def _apple_service_running() -> bool | None:
    """True/False from ``sc query``; None when the command itself fails."""
    try:
        result = run(
            ["sc", "query", APPLE_SERVICE],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=SC_TIMEOUT,
        )
    except (OSError, subprocess.SubprocessError) as exc:
        log.debug("sc query failed: %s", exc)
        return None
    if result.returncode != 0:
        return False
    for line in (result.stdout or "").splitlines():
        if line.strip().upper().startswith("STATE"):
            return "RUNNING" in line.upper()
    return False


def _apple_support_dir() -> Path:
    program_files = os.environ.get("ProgramFiles", r"C:\Program Files")
    return Path(program_files) / "Common Files" / "Apple" / "Mobile Device Support"


def _check_linux(name: str) -> dict:
    if which("usbmuxd") or which("iproxy") or exists(USBMUXD_SOCKET):
        return {"state": "ok", "detail": "", "os": name}
    return {"state": "usbmuxd_missing", "detail": "usbmuxd not installed", "os": name}


def _distro_id() -> str:
    try:
        text = OS_RELEASE.read_text(encoding="utf-8")
    except OSError:
        return ""
    ids: list[str] = []
    for line in text.splitlines():
        key, sep, value = line.partition("=")
        if sep and key.strip() in ("ID", "ID_LIKE"):
            ids.extend(value.strip().strip('"').lower().split())
    return " ".join(ids)


def install_hint(platform: str | None = None) -> str:
    name = os_name(platform)
    if name == "macos":
        return ""
    if name == "windows":
        return "Install iTunes from the Microsoft Store, then plug the iPhone in again."
    distro = _distro_id()
    if any(d in distro for d in ("debian", "ubuntu")):
        return "sudo apt install usbmuxd libimobiledevice-utils"
    if "fedora" in distro or "rhel" in distro:
        return "sudo dnf install usbmuxd libimobiledevice-utils"
    if "arch" in distro:
        return "sudo pacman -S usbmuxd libimobiledevice"
    return "Install the usbmuxd and libimobiledevice packages with your distribution's package manager."
