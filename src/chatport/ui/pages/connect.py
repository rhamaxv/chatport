"""Step 2: live status of the Android phone, the iPhone and this computer, refreshed every 3 seconds."""
from __future__ import annotations

from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QHBoxLayout, QLabel, QProgressBar, QPushButton

from chatport.i18n import t
from chatport.ui import format as fmt
from chatport.ui.pages.base import Context, Page
from chatport.ui.widgets.cards import StatusCard
from chatport.ui.workers import FunctionThread

INTERVAL_MS = 3000


def _is_ready(result: dict) -> bool:
    try:
        from chatport.core.checks import is_ready

        return bool(is_ready(result))
    except ImportError:
        pass
    android = result.get("android") or {}
    iphone = result.get("iphone") or {}
    computer = result.get("computer") or {}
    platform = computer.get("platform") or {}
    return (
        android.get("state") == "ready" and android.get("backup") == "ok"
        and iphone.get("state") == "ready" and bool(computer.get("adb"))
        and platform.get("state", "ok") == "ok"
    )


class ConnectPage(Page):
    step = "connect"
    jobs = ("adb",)
    title_key = "connect.title"
    subtitle_key = "connect.subtitle"

    def __init__(self, ctx: Context):
        super().__init__(ctx)
        self.result: dict = {}
        self._thread: FunctionThread | None = None
        self._installing = False
        self.timer = QTimer(self)
        self.timer.setInterval(INTERVAL_MS)
        self.timer.timeout.connect(self.refresh)

        self.android = StatusCard("phone-android")
        self.iphone = StatusCard("phone-iphone")
        self.computer = StatusCard("laptop")
        for card in (self.android, self.iphone, self.computer):
            self.body.addWidget(card)

        row = QHBoxLayout()
        row.setContentsMargins(0, 8, 0, 0)
        self.install_button = QPushButton()
        self.install_button.setProperty("variant", "primary")
        self.install_button.clicked.connect(self.start_job)
        self.install_bar = QProgressBar()
        self.install_bar.setRange(0, 100)
        self.install_bar.setTextVisible(False)
        self.install_label = QLabel()
        self.install_label.setProperty("role", "muted")
        row.addWidget(self.install_button, 0)
        row.addWidget(self.install_bar, 1)
        row.addWidget(self.install_label, 0)
        row.addStretch(1)
        self.computer.extra.addLayout(row)
        self._show_install(False)
        self.retranslate()

    # ----- lifecycle ---------------------------------------------------------------------------

    def on_enter(self) -> None:
        self.refresh()
        self.timer.start()

    def on_leave(self) -> None:
        self.timer.stop()
        self.wait()

    def wait(self) -> None:
        if self._thread is not None and self._thread.isRunning():
            self._thread.wait(5000)

    def refresh(self) -> None:
        if self._thread is not None and self._thread.isRunning():
            return
        if self.ctx.checks_fn is None:
            return
        self._thread = FunctionThread(self.ctx.checks_fn, self)
        self._thread.result.connect(self._on_result)
        self._thread.failed.connect(lambda _name: None)
        self._thread.start()

    def _on_result(self, result: object) -> None:
        if not isinstance(result, dict):
            return
        self.result = result
        self.ctx.last_connect = result
        self.render()
        self.continue_changed.emit(self.can_continue())

    def can_continue(self) -> bool:
        return bool(self.result) and _is_ready(self.result) and not self._installing

    def stats(self) -> dict:
        iphone = self.result.get("iphone") or {}
        android = self.result.get("android") or {}
        return {
            "iphone_encrypted": bool(iphone.get("encrypted")),
            "iphone_find_my": bool(iphone.get("find_my")),
            "iphone_name": iphone.get("name"),
            "android_model": android.get("model"),
        }

    # ----- adb install -------------------------------------------------------------------------

    def start_job(self) -> None:
        self.clear_error()
        self._installing = True
        self.install_bar.setValue(0)
        self._show_install(True, running=True)
        self.continue_changed.emit(False)
        self.ctx.runner.install_adb()

    def on_event(self, event) -> None:
        if event.kind == "progress":
            if event.pct is None:
                self.install_bar.setRange(0, 0)
            else:
                self.install_bar.setRange(0, 100)
                self.install_bar.setValue(int(event.pct))
            self.install_label.setText(t("connect.installing_adb", pct=int(event.pct or 0)))
        elif event.kind == "done":
            self._installing = False
            self._show_install(False)
            self.refresh()
        elif event.kind == "error":
            self._installing = False
            self._show_install(True, running=False)
            super().on_event(event)

    def _show_install(self, visible: bool, running: bool = False) -> None:
        self.install_button.setVisible(visible and not running)
        self.install_bar.setVisible(visible and running)
        self.install_label.setVisible(visible and running)

    # ----- rendering ---------------------------------------------------------------------------

    def retranslate(self) -> None:
        super().retranslate()
        self.install_button.setText(t("connect.install_adb"))
        self.render()

    def render(self) -> None:
        r = self.result
        if not r:
            for card, key in ((self.android, "connect.android.title"), (self.iphone, "connect.iphone.title"),
                              (self.computer, "connect.computer.title")):
                card.set_state(t(key), t("connect.checking"), "gray")
            return
        self._render_android(r.get("android") or {})
        self._render_iphone(r.get("iphone") or {})
        self._render_computer(r.get("computer") or {})

    def _render_android(self, a: dict) -> None:
        state = a.get("state", "missing")
        if state == "ready":
            backup = a.get("backup", "none")
            if backup == "ok":
                status = t("connect.android.ready", model=a.get("model") or "Android")
                status += "\n" + t("connect.android.backup.ok", age=fmt.age(a.get("backup_age_s")))
                tone = "green"
            else:
                status = t("connect.android.ready", model=a.get("model") or "Android")
                status += "\n" + t(f"connect.android.backup.{backup}")
                tone = "amber" if backup == "none" else "red"
        else:
            status = t(f"connect.android.{state}")
            tone = "amber" if state in ("missing", "unauthorized") else "red"
        self.android.set_state(t("connect.android.title"), status, tone)

    def _render_iphone(self, i: dict) -> None:
        state = i.get("state", "missing")
        if state == "ready":
            status = t("connect.iphone.ready", name=i.get("name") or "iPhone", ios=i.get("ios") or "")
            notes = []
            if i.get("encrypted"):
                notes.append(t("connect.iphone.encrypted"))
            if i.get("find_my"):
                notes.append(t("connect.iphone.find_my"))
            if notes:
                status += "\n" + "\n".join(notes)
            tone = "green"
        else:
            status = t(f"connect.iphone.{state}")
            tone = "amber"
        self.iphone.set_state(t("connect.iphone.title"), status, tone)

    def _render_computer(self, c: dict) -> None:
        platform = c.get("platform") or {}
        problems = []
        if not c.get("adb"):
            problems.append(t("connect.computer.no_adb"))
        if platform.get("state", "ok") != "ok":
            problems.append(t(f"connect.computer.platform.{platform.get('state')}"))
        free = fmt.bytes_text(c.get("free_bytes"))
        if problems:
            status = "\n".join(problems) + "\n" + t("connect.computer.free", free=free)
            tone = "red"
        else:
            status = t("connect.computer.ready", free=free)
            tone = "green"
        self.computer.set_state(t("connect.computer.title"), status, tone)
        if not self._installing:
            self._show_install(not c.get("adb"))
