"""The real wiring must tell the engine where adb is, both at start and right after an install."""
from __future__ import annotations

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from chatport import app as app_module
from chatport.core.state import State
from chatport.tools import adb as tools_adb


def test_checks_point_engine_at_freshly_found_adb(monkeypatch, tmp_path):
    used: list[str] = []
    found = {"path": None}
    monkeypatch.setattr(tools_adb, "find", lambda adb_dir: found["path"])
    monkeypatch.setattr(tools_adb, "use", lambda path: used.append(path))
    monkeypatch.setattr(app_module.paths, "adb_dir", lambda: tmp_path)
    monkeypatch.setattr(app_module.paths, "work_dir", lambda: tmp_path)
    monkeypatch.setattr("chatport.core.checks.connect_checks",
                        lambda engine, adb_path, work_root, platform_check: {"adb": adb_path})

    runner, checks_fn, _ = app_module.build_real(State(tmp_path / "state.json"))
    assert used == []                      # nothing found at start

    found["path"] = "/fresh/adb"           # installed a moment ago, outside this process' knowledge
    assert checks_fn()["adb"] == "/fresh/adb"
    assert used == ["/fresh/adb"]          # the engine was pointed at it before any status call


def test_installer_points_engine_at_downloaded_adb(monkeypatch, tmp_path):
    used: list[str] = []
    monkeypatch.setattr(tools_adb, "find", lambda adb_dir: None)
    monkeypatch.setattr(tools_adb, "use", lambda path: used.append(path))
    monkeypatch.setattr(tools_adb, "download", lambda adb_dir, cb: "/downloaded/adb")
    monkeypatch.setattr(app_module.paths, "adb_dir", lambda: tmp_path)
    monkeypatch.setattr(app_module.paths, "work_dir", lambda: tmp_path)

    runner, _, _ = app_module.build_real(State(tmp_path / "state.json"))
    assert runner._adb_installer(lambda done, total: None) == "/downloaded/adb"
    assert used == ["/downloaded/adb"]
