"""Drive the whole wizard with the fake runner, in both themes."""
from __future__ import annotations

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest
from PySide6.QtCore import Qt

from chatport import i18n
from chatport.core.state import State
from chatport.ui import theme
from chatport.ui.window import MainWindow
from fake_runner import FakeRunner, fake_checks, fake_checks_missing, fake_ready_checks

KEY = "0123456789abcdef" * 4
TIMEOUT = 5000


@pytest.fixture(params=["light", "dark"])
def themed(request, qapp):
    theme.apply(qapp, request.param == "dark")
    yield request.param
    theme.apply(qapp, False)


@pytest.fixture(autouse=True)
def english():
    i18n.set_language("en")
    yield
    i18n.set_language("en")


def make_window(qtbot, tmp_path, runner=None, checks=fake_checks, language="en", cleanup=None):
    runner = runner or FakeRunner(interval_ms=5)
    state = State(tmp_path / "state.json").load()
    window = MainWindow(runner, state, checks, language, ready_checks_fn=fake_ready_checks,
                        cleanup=cleanup or (lambda also: None), log_path=tmp_path / "chatport.log")
    qtbot.addWidget(window)
    window.show()
    return window, runner, state


def click_continue(qtbot, window):
    qtbot.waitUntil(window.continue_button.isEnabled, timeout=TIMEOUT)
    qtbot.mouseClick(window.continue_button, Qt.MouseButton.LeftButton)


def wait_page(qtbot, window, step):
    qtbot.waitUntil(lambda: window.current == step, timeout=TIMEOUT)


def walk_to_copy(qtbot, window):
    assert window.current == "welcome"
    click_continue(qtbot, window)
    wait_page(qtbot, window, "connect")
    click_continue(qtbot, window)
    wait_page(qtbot, window, "key")
    window.pages["key"].grid.paste(KEY)
    assert window.pages["key"].grid.text() == KEY
    click_continue(qtbot, window)
    wait_page(qtbot, window, "copy")


def test_full_flow(qtbot, tmp_path, themed):
    window, runner, state = make_window(qtbot, tmp_path)
    walk_to_copy(qtbot, window)
    qtbot.waitUntil(lambda: window.pages["copy"].result is not None, timeout=TIMEOUT)
    assert window.pages["copy"].summary.stats["messages"].value.text() == "61,204"
    click_continue(qtbot, window)
    wait_page(qtbot, window, "prepare")
    assert not window.continue_button.isEnabled()
    prepare = window.pages["prepare"]
    prepare.check_iphone()
    qtbot.waitUntil(lambda: prepare.checklist.rows["whatsapp"].live is True, timeout=TIMEOUT)
    prepare.checklist.rows["airplane"].box.setChecked(True)
    click_continue(qtbot, window)
    wait_page(qtbot, window, "backup")
    qtbot.waitUntil(lambda: window.pages["backup"].result is not None, timeout=TIMEOUT)
    assert "1,200" in window.pages["backup"].done_card.label.text()
    click_continue(qtbot, window)
    wait_page(qtbot, window, "build")
    qtbot.waitUntil(lambda: window.pages["build"].result is not None, timeout=TIMEOUT)
    missed = window.pages["build"].coverage.missed.lines.text()
    assert "4,000 reactions" in missed and "310 deleted messages" in missed and "21 media files" in missed
    click_continue(qtbot, window)
    wait_page(qtbot, window, "restore")
    assert window.continue_button.text() == "Restore now"
    click_continue(qtbot, window)
    qtbot.waitUntil(lambda: not window.back_button.isEnabled(), timeout=TIMEOUT)
    wait_page(qtbot, window, "done")
    assert state.current() == "done"
    assert state.done("restore") and state.done("copy")
    assert window.continue_button.text() == "Finish"
    assert not window.back_button.isVisible()
    assert [c[0] for c in runner.calls] == ["key", "copy", "backup", "build", "restore"]
    assert runner.calls[0] == ("key", 64) and runner.calls[2] == ("backup", False)


def test_error_renders_card_with_action(qtbot, tmp_path, themed):
    runner = FakeRunner(interval_ms=5)
    runner.script["copy"] = "android_copy_failed"
    window, runner, state = make_window(qtbot, tmp_path, runner=runner)
    walk_to_copy(qtbot, window)
    page = window.pages["copy"]
    qtbot.waitUntil(page.error.isVisible, timeout=TIMEOUT)
    assert page.error.title.text() == "Copying from the Android phone failed"
    assert page.error.button.isVisible() and page.error.button.text() == "Try again"
    assert not window.continue_button.isEnabled()
    runner.script["copy"] = "ok"
    qtbot.mouseClick(page.error.button, Qt.MouseButton.LeftButton)
    qtbot.waitUntil(lambda: page.result is not None, timeout=TIMEOUT)
    assert not page.error.isVisible()


def test_log_action_offers_copy_log(qtbot, tmp_path):
    runner = FakeRunner(interval_ms=5)
    runner.script["build"] = "build_failed"
    window, runner, state = make_window(qtbot, tmp_path, runner=runner)
    (tmp_path / "chatport.log").write_text("line one\n", encoding="utf-8")
    for step in ("welcome", "connect", "key", "copy", "prepare", "backup"):
        state.mark(step)
    window.go("build")
    page = window.pages["build"]
    qtbot.waitUntil(page.error.isVisible, timeout=TIMEOUT)
    assert page.error.log_button.isVisible() and page.error.log_button.text() == "Copy log"
    assert not page.error.button.isVisible()
    qtbot.mouseClick(page.error.log_button, Qt.MouseButton.LeftButton)
    from PySide6.QtWidgets import QApplication

    assert "line one" in QApplication.clipboard().text()


def test_back_action_goes_to_target_step(qtbot, tmp_path):
    runner = FakeRunner(interval_ms=5)
    runner.script["restore"] = "nothing_to_restore"
    window, runner, state = make_window(qtbot, tmp_path, runner=runner)
    for step in ("welcome", "connect", "key", "copy", "prepare", "backup", "build"):
        state.mark(step)
    window.go("restore")
    click_continue(qtbot, window)
    page = window.pages["restore"]
    qtbot.waitUntil(page.error.isVisible, timeout=TIMEOUT)
    assert page.error.button.text() == "Go back"
    qtbot.mouseClick(page.error.button, Qt.MouseButton.LeftButton)
    wait_page(qtbot, window, "backup")
    assert not state.done("backup") and not state.done("build")


def test_connect_gates_continue_and_offers_adb_install(qtbot, tmp_path):
    window, runner, state = make_window(qtbot, tmp_path, checks=fake_checks_missing)
    click_continue(qtbot, window)
    wait_page(qtbot, window, "connect")
    page = window.pages["connect"]
    qtbot.waitUntil(lambda: bool(page.result), timeout=TIMEOUT)
    assert not window.continue_button.isEnabled()
    assert page.install_button.isVisible()
    qtbot.mouseClick(page.install_button, Qt.MouseButton.LeftButton)
    qtbot.waitUntil(lambda: ("adb",) in runner.calls, timeout=TIMEOUT)
    qtbot.waitUntil(lambda: not runner.busy(), timeout=TIMEOUT)
    assert "Plug in the Android phone" in page.android.status.text()


def test_resume_at_saved_step(qtbot, tmp_path):
    window, runner, state = make_window(qtbot, tmp_path)
    walk_to_copy(qtbot, window)
    qtbot.waitUntil(lambda: window.pages["copy"].result is not None, timeout=TIMEOUT)
    click_continue(qtbot, window)
    wait_page(qtbot, window, "prepare")
    window.close()
    again, _runner, state2 = make_window(qtbot, tmp_path)
    assert state2.current() == "prepare"
    assert again.current == "prepare"
    assert again.rail._current == "prepare"


def test_back_resets_later_steps(qtbot, tmp_path):
    window, runner, state = make_window(qtbot, tmp_path)
    click_continue(qtbot, window)
    wait_page(qtbot, window, "connect")
    click_continue(qtbot, window)
    wait_page(qtbot, window, "key")
    assert state.done("connect")
    qtbot.mouseClick(window.back_button, Qt.MouseButton.LeftButton)
    wait_page(qtbot, window, "connect")
    assert not state.done("connect")


def test_language_switch_changes_title(qtbot, tmp_path, monkeypatch):
    table = dict(i18n._table("id"))
    table["welcome.title"] = "Pindahkan WhatsApp ke iPhone"
    monkeypatch.setitem(i18n._tables, "id", table)
    window, runner, state = make_window(qtbot, tmp_path)
    english = window.pages["welcome"].title.text()
    qtbot.mouseClick(window.lang_buttons["id"], Qt.MouseButton.LeftButton)
    assert i18n.language() == "id"
    assert window.pages["welcome"].title.text() == "Pindahkan WhatsApp ke iPhone" != english
    assert state.lang == "id"
    qtbot.mouseClick(window.lang_buttons["en"], Qt.MouseButton.LeftButton)
    assert window.pages["welcome"].title.text() == english


def test_theme_toggle(qtbot, tmp_path, qapp):
    window, runner, state = make_window(qtbot, tmp_path)
    before = theme.current().dark
    qtbot.mouseClick(window.theme_button, Qt.MouseButton.LeftButton)
    assert theme.current().dark != before
    theme.apply(qapp, False)


def test_key_grid_typing_and_paste(qtbot, tmp_path):
    from chatport.ui.widgets.key_grid import KeyGrid

    grid = KeyGrid()
    qtbot.addWidget(grid)
    grid.show()
    grid.boxes[0].setFocus()
    qtbot.keyClicks(grid.boxes[0], "ABCD")
    assert grid.boxes[0].text() == "abcd"
    qtbot.keyClicks(grid.boxes[1], "12")
    assert grid.boxes[1].text() == "12"
    assert not grid.is_complete()
    grid.paste("  ".join(KEY[i:i + 4] for i in range(0, 64, 4)).upper())
    assert grid.text() == KEY and grid.is_complete()
    grid.set_text("")
    assert grid.text() == ""


def test_done_page_cleanup_calls_back(qtbot, tmp_path, monkeypatch):
    calls = []
    window, runner, state = make_window(qtbot, tmp_path, cleanup=calls.append)
    for step in ("welcome", "connect", "key", "copy", "prepare", "backup", "build", "restore"):
        state.mark(step)
    window.go("done")
    from PySide6.QtWidgets import QDialog

    from chatport.ui.pages import done as done_module

    monkeypatch.setattr(done_module.CleanupDialog, "exec", lambda self: QDialog.DialogCode.Accepted)
    qtbot.mouseClick(window.pages["done"].cleanup_card.button, Qt.MouseButton.LeftButton)
    assert calls == [False]
    assert not window.pages["done"].cleanup_card.button.isEnabled()
