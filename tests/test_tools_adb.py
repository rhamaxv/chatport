import os
import shutil
import sys
import zipfile
from pathlib import Path

import pytest

from chatport.tools import adb
from chatport.tools.download import DownloadError

WINDOWS = sys.platform == "win32"
HOST = sys.platform
VERSION_LINE = "Android Debug Bridge version 35.0.2-12147458"
MARKER = b"CHATPORT-FAKE-ADB"
posix_only = pytest.mark.skipif(WINDOWS, reason="needs a runnable fake adb named adb, not adb.exe")


def write_fake_adb(directory: Path, stem: str, lines: list[str], exit_code: int = 0) -> Path:
    """A script that prints ``lines`` and exits. .cmd on Windows, sh elsewhere."""
    if WINDOWS:
        path = directory / f"{stem}.cmd"
        body = ["@echo off", *[f"echo {line}" for line in lines], f"exit /b {exit_code}"]
        path.write_text("\r\n".join(body) + "\r\n")
    else:
        path = directory / stem
        body = ["#!/bin/sh", *[f"echo '{line}'" for line in lines], f"exit {exit_code}"]
        path.write_text("\n".join(body) + "\n")
        path.chmod(0o755)
    return path


def _add(zf: zipfile.ZipFile, name: str, data: bytes, mode: int = 0o644) -> None:
    info = zipfile.ZipInfo(name)
    info.external_attr = (mode & 0o7777) << 16
    zf.writestr(info, data)


def make_zip(path: Path, members: dict[str, tuple[bytes, int]]) -> Path:
    with zipfile.ZipFile(path, "w") as zf:
        for name, (data, mode) in members.items():
            _add(zf, name, data, mode)
    return path


def serve_zip(monkeypatch, zip_path: Path, calls: list) -> None:
    def fake_download(url, target, on_progress, timeout=60):
        calls.append(url)
        on_progress(0, 10)
        shutil.copyfile(zip_path, target)
        on_progress(10, 10)

    monkeypatch.setattr(adb, "download_file", fake_download)


def fake_version(monkeypatch, seen: list) -> None:
    """Stand in for running the binary: a file carrying MARKER "runs", anything else does not."""

    def version(path: str) -> str | None:
        seen.append(path)
        return "35.0.2" if MARKER in Path(path).read_bytes() else None

    monkeypatch.setattr(adb, "version", version)


def runnable_adb_bytes() -> bytes:
    return b"#!/bin/sh\n# " + MARKER + b"\necho '" + VERSION_LINE.encode() + b"'\n"


def test_binary_name_and_bundled(tmp_path):
    assert adb.binary_name("win32") == "adb.exe"
    assert adb.binary_name("darwin") == "adb"
    assert adb.binary_name("linux") == "adb"
    assert adb.bundled(tmp_path, "linux") == tmp_path / "platform-tools" / "adb"
    assert adb.bundled(tmp_path, "win32").name == "adb.exe"


def test_urls_cover_three_platforms():
    assert set(adb.URLS) == {"darwin", "win32", "linux"}
    for url in adb.URLS.values():
        assert url.startswith("https://dl.google.com/android/repository/platform-tools-latest-")


def test_executable_check(tmp_path):
    plain = tmp_path / "adb"
    plain.write_text("x")
    exe = tmp_path / "adb.exe"
    exe.write_text("x")
    assert not adb._executable(tmp_path / "missing")
    if WINDOWS:
        assert adb._executable(exe)
        assert not adb._executable(plain)
    else:
        plain.chmod(0o644)
        assert not adb._executable(plain)
        plain.chmod(0o755)
        assert adb._executable(plain)


def test_find_prefers_bundled(tmp_path):
    exe = adb.bundled(tmp_path, HOST)
    exe.parent.mkdir(parents=True)
    exe.write_text("fake")
    exe.chmod(0o755)
    assert adb.find(tmp_path, HOST, which=lambda name: "/elsewhere/adb") == str(exe)


def test_find_skips_non_executable_bundled(tmp_path):
    # Named plain "adb": no exec bit on POSIX, no executable suffix on Windows.
    exe = adb.bundled(tmp_path, "darwin")
    exe.parent.mkdir(parents=True)
    exe.write_text("fake")
    exe.chmod(0o644)
    assert adb.find(tmp_path, "darwin", which=lambda name: "/elsewhere/adb") == "/elsewhere/adb"


def test_find_falls_back_to_common_locations(tmp_path, monkeypatch):
    fallback = tmp_path / "sdk" / adb.binary_name()
    fallback.parent.mkdir()
    fallback.write_text("fake")
    fallback.chmod(0o755)
    monkeypatch.setattr(adb, "_common_locations", lambda plat: [str(tmp_path / "missing"), str(fallback)])
    assert adb.find(tmp_path, HOST, which=lambda name: None) == str(fallback)


def test_find_returns_none_when_nothing(tmp_path, monkeypatch):
    monkeypatch.setattr(adb, "_common_locations", lambda plat: [str(tmp_path / "missing")])
    assert adb.find(tmp_path, HOST, which=lambda name: None) is None


def test_common_locations_per_platform(monkeypatch, tmp_path):
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path / "local"))
    monkeypatch.setenv("ProgramData", str(tmp_path / "pd"))
    win = adb._common_locations("win32")
    assert all(isinstance(p, str) and p.endswith("adb.exe") for p in win)
    assert any("chocolatey" in p for p in win)
    mac = adb._common_locations("darwin")
    assert mac[0] == "/opt/homebrew/bin/adb"  # literal, never normalized by the host's os.path
    linux = adb._common_locations("linux")
    assert linux[0] == "/usr/bin/adb"


def test_common_locations_windows_without_localappdata(monkeypatch):
    monkeypatch.delenv("LOCALAPPDATA", raising=False)
    win = adb._common_locations("win32")
    assert len(win) == 1 and "chocolatey" in win[0]


def test_version_parses_output(tmp_path):
    exe = write_fake_adb(tmp_path, "adb", [VERSION_LINE, "Version 35.0.2"])
    assert adb.version(str(exe)) == "35.0.2-12147458"


def test_version_none_on_missing_or_bad_output(tmp_path):
    assert adb.version(str(tmp_path / "nope")) is None
    quiet = write_fake_adb(tmp_path, "quiet", ["hello"])
    assert adb.version(str(quiet)) is None
    failing = write_fake_adb(tmp_path, "fail", ["Android Debug Bridge version 1.0"], exit_code=1)
    assert adb.version(str(failing)) is None


def test_safe_member_filter():
    assert adb._safe_member("platform-tools/adb")
    assert adb._safe_member("platform-tools/lib64/libc++.so")
    assert not adb._safe_member("platform-tools/../evil")
    assert not adb._safe_member("other/adb")
    assert not adb._safe_member("../platform-tools/adb")
    assert not adb._safe_member("platform-tools\\..\\evil")


def test_extract_rejects_zip_slip(tmp_path):
    archive = make_zip(
        tmp_path / "slip.zip",
        {
            "platform-tools/../evil.txt": (b"bad", 0o644),
            "../outside.txt": (b"bad", 0o644),
            "platform-tools/ok.txt": (b"good", 0o644),
        },
    )
    dest = tmp_path / "dest"
    dest.mkdir()
    adb._extract(archive, dest)
    assert (dest / "platform-tools" / "ok.txt").read_bytes() == b"good"
    assert not (dest / "evil.txt").exists()
    assert not (tmp_path / "evil.txt").exists()
    assert not (tmp_path / "outside.txt").exists()
    assert sorted(p.name for p in dest.rglob("*") if p.is_file()) == ["ok.txt"]


def test_download_extracts_and_verifies(tmp_path, monkeypatch):
    name = adb.binary_name(HOST)
    archive = make_zip(
        tmp_path / "pt.zip",
        {
            "platform-tools/": (b"", 0o755),
            f"platform-tools/{name}": (runnable_adb_bytes(), 0o644),
            "platform-tools/NOTICE.txt": (b"notice", 0o644),
            "platform-tools/lib64/libfoo.so": (b"so", 0o755),
            "platform-tools/../escape": (b"bad", 0o644),
            "README": (b"top level, must be skipped", 0o644),
        },
    )
    calls: list = []
    progress: list = []
    verified: list = []
    serve_zip(monkeypatch, archive, calls)
    fake_version(monkeypatch, verified)
    adb_dir = tmp_path / "adb_dir"

    result = adb.download(adb_dir, lambda d, t: progress.append((d, t)), platform=HOST)

    assert calls == [adb.URLS[HOST]]
    assert progress == [(0, 10), (10, 10)]
    exe = adb_dir / "platform-tools" / name
    assert result == str(exe)
    assert exe.read_bytes() == runnable_adb_bytes()
    assert len(verified) == 1 and Path(verified[0]).name == name
    if not WINDOWS:
        assert exe.stat().st_mode & 0o755 == 0o755
        assert (adb_dir / "platform-tools" / "lib64" / "libfoo.so").stat().st_mode & 0o111
    assert (adb_dir / "platform-tools" / "NOTICE.txt").read_bytes() == b"notice"
    assert not (adb_dir / "escape").exists()
    assert not (adb_dir / "README").exists()
    leftovers = [p for p in adb_dir.iterdir() if p.name != "platform-tools"]
    assert leftovers == []


@posix_only
def test_download_runs_real_adb_version(tmp_path, monkeypatch):
    """Full pipeline including the real subprocess verification. The fake must be named adb."""
    archive = make_zip(tmp_path / "pt.zip", {"platform-tools/adb": (runnable_adb_bytes(), 0o644)})
    serve_zip(monkeypatch, archive, [])
    adb_dir = tmp_path / "adb_dir"
    result = adb.download(adb_dir, lambda d, t: None, platform=HOST)
    assert adb.version(result) == "35.0.2-12147458"
    assert os.access(result, os.X_OK)


def test_download_replaces_existing_install(tmp_path, monkeypatch):
    name = adb.binary_name(HOST)
    adb_dir = tmp_path / "adb_dir"
    old = adb_dir / "platform-tools" / "stale.txt"
    old.parent.mkdir(parents=True)
    old.write_text("old")
    archive = make_zip(tmp_path / "pt.zip", {f"platform-tools/{name}": (runnable_adb_bytes(), 0o755)})
    serve_zip(monkeypatch, archive, [])
    fake_version(monkeypatch, [])
    adb.download(adb_dir, lambda d, t: None, platform=HOST)
    assert not old.exists()
    assert (adb_dir / "platform-tools" / name).exists()


def test_download_fails_without_adb_binary(tmp_path, monkeypatch):
    archive = make_zip(tmp_path / "pt.zip", {"platform-tools/NOTICE.txt": (b"x", 0o644)})
    serve_zip(monkeypatch, archive, [])
    fake_version(monkeypatch, [])
    adb_dir = tmp_path / "adb_dir"
    with pytest.raises(adb.AdbDownloadError):
        adb.download(adb_dir, lambda d, t: None, platform=HOST)
    assert list(adb_dir.iterdir()) == []


def test_download_fails_when_adb_does_not_run(tmp_path, monkeypatch):
    name = adb.binary_name(HOST)
    archive = make_zip(tmp_path / "pt.zip", {f"platform-tools/{name}": (b"not a program", 0o755)})
    serve_zip(monkeypatch, archive, [])
    fake_version(monkeypatch, [])
    adb_dir = tmp_path / "adb_dir"
    with pytest.raises(adb.AdbDownloadError):
        adb.download(adb_dir, lambda d, t: None, platform=HOST)
    assert list(adb_dir.iterdir()) == []


def test_download_wraps_download_error(tmp_path, monkeypatch):
    def failing(url, target, on_progress, timeout=60):
        raise DownloadError("boom")

    monkeypatch.setattr(adb, "download_file", failing)
    adb_dir = tmp_path / "adb_dir"
    with pytest.raises(adb.AdbDownloadError) as info:
        adb.download(adb_dir, lambda d, t: None, platform=HOST)
    assert isinstance(info.value.__cause__, DownloadError)
    assert list(adb_dir.iterdir()) == []


def test_download_rejects_bad_zip(tmp_path, monkeypatch):
    bad = tmp_path / "bad.zip"
    bad.write_bytes(b"not a zip")
    serve_zip(monkeypatch, bad, [])
    adb_dir = tmp_path / "adb_dir"
    with pytest.raises(adb.AdbDownloadError):
        adb.download(adb_dir, lambda d, t: None, platform=HOST)
    assert list(adb_dir.iterdir()) == []


def test_download_unknown_platform(tmp_path):
    with pytest.raises(adb.AdbDownloadError):
        adb.download(tmp_path, lambda d, t: None, platform="plan9")


def test_use_points_engine_at_path():
    import wamove.android.adb as wadb

    original = wadb._adb
    try:
        adb.use("/custom/adb")
        assert wadb._adb() == "/custom/adb"
    finally:
        wadb._adb = original


class _FakeResponse:
    def __init__(self, payload: bytes, length: int | None):
        self._buf = payload
        self.headers = {"Content-Length": str(length)} if length is not None else {}

    def read(self, n: int) -> bytes:
        chunk, self._buf = self._buf[:n], self._buf[n:]
        return chunk

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False


def test_download_file_streams_with_progress(tmp_path, monkeypatch):
    import urllib.request

    from chatport.tools import download

    payload = b"x" * (download.CHUNK + 5)
    monkeypatch.setattr(urllib.request, "urlopen", lambda url, timeout: _FakeResponse(payload, len(payload)))
    seen: list = []
    target = tmp_path / "sub" / "file.bin"
    download.download_file("https://example.invalid/f", target, lambda d, t: seen.append((d, t)))
    assert target.read_bytes() == payload
    assert seen == [(0, len(payload)), (download.CHUNK, len(payload)), (len(payload), len(payload))]


def test_download_file_unknown_total_and_errors(tmp_path, monkeypatch):
    import urllib.error
    import urllib.request

    from chatport.tools import download

    monkeypatch.setattr(urllib.request, "urlopen", lambda url, timeout: _FakeResponse(b"abc", None))
    seen: list = []
    download.download_file("https://example.invalid/f", tmp_path / "f", lambda d, t: seen.append((d, t)))
    assert seen == [(0, 0), (3, 0)]

    def boom(url, timeout):
        raise urllib.error.URLError("offline")

    monkeypatch.setattr(urllib.request, "urlopen", boom)
    with pytest.raises(download.DownloadError) as info:
        download.download_file("https://example.invalid/g", tmp_path / "g", lambda d, t: None)
    assert isinstance(info.value.__cause__, urllib.error.URLError)
    assert not (tmp_path / "g").exists()
