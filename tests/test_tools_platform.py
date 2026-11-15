import subprocess
from pathlib import Path

import pytest

from chatport.tools import platform as plat


class Result:
    def __init__(self, stdout: str, returncode: int = 0):
        self.stdout = stdout
        self.returncode = returncode


SC_RUNNING = """
SERVICE_NAME: Apple Mobile Device Service
        TYPE               : 10  WIN32_OWN_PROCESS
        STATE              : 4  RUNNING
                                (STOPPABLE, NOT_PAUSABLE, ACCEPTS_SHUTDOWN)
"""

SC_STOPPED = """
SERVICE_NAME: Apple Mobile Device Service
        TYPE               : 10  WIN32_OWN_PROCESS
        STATE              : 1  STOPPED
"""


def test_os_name_mapping():
    assert plat.os_name("darwin") == "macos"
    assert plat.os_name("win32") == "windows"
    assert plat.os_name("cygwin") == "windows"
    assert plat.os_name("linux") == "linux"
    assert plat.os_name("linux2") == "linux"


def test_macos_always_ok(monkeypatch):
    monkeypatch.setattr(plat, "run", lambda *a, **k: pytest.fail("must not run anything"))
    monkeypatch.setattr(plat, "which", lambda name: pytest.fail("must not call which"))
    assert plat.check("darwin") == {"state": "ok", "detail": "", "os": "macos"}
    assert plat.install_hint("darwin") == ""


def test_windows_service_running(monkeypatch):
    seen: list = []

    def fake_run(cmd, **kwargs):
        seen.append((cmd, kwargs.get("timeout")))
        return Result(SC_RUNNING)

    monkeypatch.setattr(plat, "run", fake_run)
    result = plat.check("win32")
    assert result == {"state": "ok", "detail": "", "os": "windows"}
    assert seen == [(["sc", "query", "Apple Mobile Device Service"], 10)]


def test_windows_service_stopped(monkeypatch):
    monkeypatch.setattr(plat, "run", lambda *a, **k: Result(SC_STOPPED))
    monkeypatch.setattr(plat, "exists", lambda path: pytest.fail("no fallback when sc works"))
    result = plat.check("win32")
    assert result["state"] == "apple_service_missing"
    assert result["os"] == "windows"


def test_windows_service_not_installed(monkeypatch):
    monkeypatch.setattr(plat, "run", lambda *a, **k: Result("[SC] EnumQueryServicesStatus:OpenService FAILED 1060", 1060))
    assert plat.check("win32")["state"] == "apple_service_missing"


def test_windows_sc_failure_falls_back_to_folder(monkeypatch):
    def broken(*a, **k):
        raise FileNotFoundError("sc")

    monkeypatch.setattr(plat, "run", broken)
    monkeypatch.setenv("ProgramFiles", r"C:\Program Files")
    checked: list = []

    def fake_exists(path):
        checked.append(str(path))
        return True

    monkeypatch.setattr(plat, "exists", fake_exists)
    assert plat.check("win32")["state"] == "ok"
    assert checked and checked[0].endswith("Mobile Device Support")
    assert "Common Files" in checked[0] and "Apple" in checked[0]

    monkeypatch.setattr(plat, "exists", lambda path: False)
    assert plat.check("win32")["state"] == "apple_service_missing"


def test_windows_sc_timeout_falls_back(monkeypatch):
    def slow(*a, **k):
        raise subprocess.TimeoutExpired(cmd="sc", timeout=10)

    monkeypatch.setattr(plat, "run", slow)
    monkeypatch.setattr(plat, "exists", lambda path: False)
    assert plat.check("win32")["state"] == "apple_service_missing"


def test_windows_hint():
    hint = plat.install_hint("win32")
    assert "iTunes" in hint and "Microsoft Store" in hint


def test_linux_ok_via_which(monkeypatch):
    monkeypatch.setattr(plat, "which", lambda name: "/usr/sbin/usbmuxd" if name == "usbmuxd" else None)
    monkeypatch.setattr(plat, "exists", lambda path: False)
    assert plat.check("linux") == {"state": "ok", "detail": "", "os": "linux"}

    monkeypatch.setattr(plat, "which", lambda name: "/usr/bin/iproxy" if name == "iproxy" else None)
    assert plat.check("linux")["state"] == "ok"


def test_linux_ok_via_socket(monkeypatch):
    monkeypatch.setattr(plat, "which", lambda name: None)
    monkeypatch.setattr(plat, "exists", lambda path: Path(path) == Path("/var/run/usbmuxd"))
    assert plat.check("linux")["state"] == "ok"


def test_linux_missing(monkeypatch):
    monkeypatch.setattr(plat, "which", lambda name: None)
    monkeypatch.setattr(plat, "exists", lambda path: False)
    result = plat.check("linux")
    assert result["state"] == "usbmuxd_missing"
    assert result["os"] == "linux"


@pytest.mark.parametrize(
    "os_release, expected",
    [
        ('ID=ubuntu\nID_LIKE=debian\n', "sudo apt install usbmuxd libimobiledevice-utils"),
        ('ID="debian"\n', "sudo apt install usbmuxd libimobiledevice-utils"),
        ('ID=linuxmint\nID_LIKE="ubuntu debian"\n', "sudo apt install usbmuxd libimobiledevice-utils"),
        ("ID=fedora\n", "sudo dnf install usbmuxd libimobiledevice-utils"),
        ("ID=arch\n", "sudo pacman -S usbmuxd libimobiledevice"),
        ("ID=manjaro\nID_LIKE=arch\n", "sudo pacman -S usbmuxd libimobiledevice"),
    ],
)
def test_linux_hint_per_distro(tmp_path, monkeypatch, os_release, expected):
    release = tmp_path / "os-release"
    release.write_text(os_release)
    monkeypatch.setattr(plat, "OS_RELEASE", release)
    assert plat.install_hint("linux") == expected


def test_linux_hint_generic(tmp_path, monkeypatch):
    monkeypatch.setattr(plat, "OS_RELEASE", tmp_path / "absent")
    hint = plat.install_hint("linux")
    assert "usbmuxd" in hint and not hint.startswith("sudo")

    release = tmp_path / "os-release"
    release.write_text("ID=nixos\n")
    monkeypatch.setattr(plat, "OS_RELEASE", release)
    assert plat.install_hint("linux") == hint


def test_check_defaults_to_sys_platform(monkeypatch):
    import sys

    monkeypatch.setattr(sys, "platform", "linux")
    monkeypatch.setattr(plat, "which", lambda name: None)
    monkeypatch.setattr(plat, "exists", lambda path: False)
    assert plat.check()["os"] == "linux"
    monkeypatch.setattr(sys, "platform", "darwin")
    assert plat.check()["os"] == "macos"
