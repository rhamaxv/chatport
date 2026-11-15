import logging
import threading

import pytest
from wamove import api
from wamove.android import adb

from chatport.core.errors import ErrorCode
from chatport.core.jobs import JobRunner
from chatport.core.state import State
from fake_engine import FakeEngine

KEY_HEX = "".join(f"{i:04x}" for i in range(16))


def terminal(event):
    return event.kind in ("done", "error")


@pytest.fixture
def setup(tmp_path):
    engine = FakeEngine()
    state = State(tmp_path / "state.json")
    runner = JobRunner(engine, tmp_path / "work", state)
    yield engine, state, runner
    if runner._worker is not None:
        runner._worker.wait(5000)


def run(qtbot, runner, start):
    """Start a job, collect every event until the terminal one, return the list."""
    seen = []
    with qtbot.waitSignal(runner.event, timeout=5000, check_params_cb=terminal) as blocker:
        runner.event.connect(seen.append)
        assert start()
    runner.event.disconnect(seen.append)
    assert runner.busy() is False
    return seen


def test_copy_without_key_fails_with_key_missing(qtbot, setup):
    engine, state, runner = setup
    events = run(qtbot, runner, runner.copy)
    assert [e.kind for e in events] == ["error"]
    assert events[-1].data["code"] == ErrorCode.KEY_MISSING.value
    assert engine.calls == []
    assert not state.done("copy")


def test_check_key_stores_key_and_marks_state(qtbot, setup):
    engine, state, runner = setup
    engine.working_key = bytes.fromhex(KEY_HEX)
    events = run(qtbot, runner, lambda: runner.check_key(" ".join(KEY_HEX[i:i + 4] for i in range(0, 64, 4))))
    assert events[-1].kind == "done"
    assert events[-1].data == {"order": "as_typed"}
    assert runner.has_key()
    assert state.done("key") and state.get("key")["order"] == "as_typed"
    runner.forget_key()
    assert not runner.has_key()


def test_check_key_wrong_and_bad_format(qtbot, setup):
    engine, state, runner = setup
    engine.working_key = b"\x01" * 32
    events = run(qtbot, runner, lambda: runner.check_key(KEY_HEX))
    assert events[-1].data["code"] == ErrorCode.KEY_WRONG.value
    assert not runner.has_key()
    events = run(qtbot, runner, lambda: runner.check_key("not a key"))
    assert events[-1].data["code"] == ErrorCode.KEY_FORMAT.value
    assert ("key_sample", {}) in engine.calls and engine.calls.count(("key_sample", {})) == 1


def test_copy_merges_pull_and_decrypt_and_marks_state(qtbot, setup):
    engine, state, runner = setup
    engine.working_key = bytes.fromhex(KEY_HEX)
    run(qtbot, runner, lambda: runner.check_key(KEY_HEX))
    engine.script("pull", result={"contacts": 3, "media_bytes": 10}, progress=2)
    engine.script("decrypt", result={"chats": 7, "messages": 99})
    events = run(qtbot, runner, runner.copy)
    done = [e for e in events if terminal(e)]
    assert len(done) == 1 and done[0].kind == "done"
    assert done[0].data == {"contacts": 3, "media_bytes": 10, "chats": 7, "messages": 99}
    assert all(e.job == "copy" for e in events)
    assert state.done("copy") and state.get("copy")["messages"] == 99
    assert ("decrypt", {"key_len": 32}) in engine.calls


def test_busy_rejects_second_job(qtbot, setup):
    engine, state, runner = setup
    engine.script("backup", wait_cancel=False, progress=0, result={"udid": "x"})
    started = threading.Event()
    original = engine.backup

    def slow_backup(work, report, password, reuse=False):
        started.set()
        return original(work, report, password, reuse)
    engine.backup = slow_backup
    with qtbot.waitSignal(runner.event, timeout=5000, check_params_cb=terminal):
        assert runner.backup("pw")
        assert runner.busy() and runner.job_name() == "backup"
        assert runner.build("pw") is False
        assert runner.install_adb() is False
    assert not runner.busy() and runner.job_name() is None
    assert state.done("backup")
    assert ("backup", {"password": "pw", "reuse": False}) in engine.calls


def test_cancel_yields_cancelled(qtbot, setup):
    engine, state, runner = setup
    engine.script("build", wait_cancel=True)
    with qtbot.waitSignal(runner.event, timeout=5000, check_params_cb=terminal) as blocker:
        assert runner.build(None)
        runner.cancel()
    event = blocker.args[0]
    assert event.kind == "error" and event.data["code"] == ErrorCode.CANCELLED.value
    assert not state.done("build")


def test_cancel_is_ignored_during_restore(qtbot, setup):
    engine, state, runner = setup
    engine.script("restore", result={"used_bytes_before": 1}, progress=1)
    with qtbot.waitSignal(runner.event, timeout=5000, check_params_cb=terminal) as blocker:
        assert runner.restore("pw")
        runner.cancel()
    assert not runner._cancel.is_set()
    assert blocker.args[0].kind == "done"
    assert state.done("restore")
    assert ("restore", {"source": "patched", "password": "pw"}) in engine.calls


def test_undo_uses_pristine_and_does_not_mark(qtbot, setup):
    engine, state, runner = setup
    events = run(qtbot, runner, lambda: runner.undo(None))
    assert events[-1].kind == "done" and events[-1].job == "undo"
    assert ("restore", {"source": "pristine", "password": None}) in engine.calls
    assert state.current() == "welcome"


@pytest.mark.parametrize("exc,code", [
    (api.NotEnoughSpace(5, 1), ErrorCode.NO_SPACE),
    (api.PasswordNeeded(), ErrorCode.PASSWORD_NEEDED),
    (adb.AdbError("no Android phone found"), ErrorCode.NO_ANDROID),
    (RuntimeError("x"), ErrorCode.UNKNOWN),
])
def test_errors_are_mapped(qtbot, setup, exc, code):
    engine, state, runner = setup
    engine.script("backup", raises=exc)
    events = run(qtbot, runner, lambda: runner.backup("pw"))
    assert len(events) == 1
    assert events[0].kind == "error" and events[0].data["code"] == code.value
    if code is ErrorCode.NO_SPACE:
        assert events[0].data["needed"] == 5
    assert not state.done("backup")


def test_build_done_marks_state_and_passes_cancel(qtbot, setup):
    engine, state, runner = setup
    engine.script("build", result={"messages_added": 4})
    events = run(qtbot, runner, lambda: runner.build("pw"))
    assert events[-1].kind == "done" and events[-1].job == "build"
    assert state.get("build")["messages_added"] == 4


def test_install_adb_reports_progress(qtbot, tmp_path):
    def installer(on_progress):
        on_progress(50, 100)
        on_progress(100, 100)
        return "/tools/adb"
    runner = JobRunner(FakeEngine(), tmp_path, State(tmp_path / "s.json"), adb_installer=installer)
    events = run(qtbot, runner, runner.install_adb)
    progress = [e for e in events if e.kind == "progress"]
    assert progress and progress[0].job == "adb"
    assert progress[-1].data == {"done_bytes": 100, "total_bytes": 100} and progress[-1].pct == 100
    assert events[-1].kind == "done" and events[-1].data == {"path": "/tools/adb"}
    runner._worker.wait(5000)


def test_install_adb_without_installer_is_rejected(tmp_path):
    runner = JobRunner(FakeEngine(), tmp_path, State(tmp_path / "s.json"))
    assert runner.install_adb() is False


def test_progress_is_throttled(qtbot, setup):
    engine, state, runner = setup
    engine.script("backup", progress=200, result={})
    events = run(qtbot, runner, lambda: runner.backup(None))
    progress = [e for e in events if e.kind == "progress"]
    assert 1 <= len(progress) <= 5
    assert progress[-1].pct == 100


def test_busy_changed_signal(qtbot, setup):
    engine, state, runner = setup
    flags = []
    runner.busy_changed.connect(flags.append)
    run(qtbot, runner, lambda: runner.backup(None))
    assert flags == [True, False]


def test_log_never_contains_key(qtbot, setup, caplog):
    engine, state, runner = setup
    engine.script("pull", raises=RuntimeError(f"leak {KEY_HEX}"))
    engine.working_key = bytes.fromhex(KEY_HEX)
    run(qtbot, runner, lambda: runner.check_key(KEY_HEX))
    with caplog.at_level(logging.INFO, logger="chatport.jobs"):
        events = run(qtbot, runner, runner.copy)
    assert events[-1].data["code"] == ErrorCode.UNKNOWN.value
    assert KEY_HEX not in caplog.text
    assert KEY_HEX not in events[-1].data["detail"]


def test_backup_passes_reuse_to_engine(qtbot, tmp_path):
    from chatport.core.jobs import JobRunner
    from chatport.core.state import State
    engine = FakeEngine()
    engine.existing_age = 42.0
    runner = JobRunner(engine, tmp_path, State(tmp_path / "s.json").load())
    assert runner.existing_backup_age("udid") == 42.0
    assert runner.existing_backup_age(None) is None
    with qtbot.waitSignal(runner.event, timeout=5000, check_params_cb=lambda e: e.kind == "done"):
        assert runner.backup(None, reuse=True)
    assert any(name == "backup" and kw.get("reuse") is True for name, kw in engine.calls)
