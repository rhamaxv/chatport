from chatport.core import checks
from fake_engine import FakeEngine

GOOD = {
    "android": {"state": "ready", "backup": "ok"},
    "iphone": {"state": "ready"},
    "computer": {"free_bytes": 3 * 1024 ** 3, "adb": "/usr/bin/adb", "platform": {"state": "ok"}},
}


def variant(**changes) -> dict:
    result = {k: dict(v) for k, v in GOOD.items()}
    for section, patch in changes.items():
        result[section].update(patch)
    return result


def test_is_ready_when_everything_is_green():
    assert checks.is_ready(GOOD)


def test_is_ready_rejects_each_failing_card():
    assert not checks.is_ready(variant(android={"state": "unauthorized"}))
    assert not checks.is_ready(variant(android={"backup": "none"}))
    assert not checks.is_ready(variant(iphone={"state": "untrusted"}))
    assert not checks.is_ready(variant(computer={"platform": {"state": "usbmuxd_missing"}}))
    assert not checks.is_ready(variant(computer={"adb": None}))
    assert not checks.is_ready(variant(computer={"free_bytes": 2 * 1024 ** 3}))
    assert not checks.is_ready({})


def test_connect_checks_shape(tmp_path):
    engine = FakeEngine()
    engine.script("android_status", result={"state": "ready", "backup": "ok"})
    engine.script("iphone_status", result={"state": "ready"})
    result = checks.connect_checks(engine, "/adb", tmp_path, lambda: {"state": "ok", "detail": ""})
    assert result["android"] == {"state": "ready", "backup": "ok"}
    assert result["iphone"] == {"state": "ready"}
    assert result["computer"]["adb"] == "/adb"
    assert result["computer"]["platform"]["state"] == "ok"
    assert result["computer"]["free_bytes"] > 0


def test_connect_checks_without_adb_skips_android(tmp_path):
    engine = FakeEngine()
    result = checks.connect_checks(engine, None, tmp_path / "missing", lambda: {"state": "ok"})
    assert result["android"] == {"state": "no_adb"}
    assert ("android_status", {}) not in engine.calls


def test_ready_checks_asks_for_apps():
    engine = FakeEngine()
    engine.script("iphone_status", result={"state": "ready", "whatsapp": True})
    assert checks.ready_checks(engine) == {"iphone": {"state": "ready", "whatsapp": True}}
    assert engine.calls == [("iphone_status", {"with_apps": True})]
