"""Step 2: live checks every 3 seconds. The phone panels carry the phones' state; the middle column shows
this computer and the adb install control."""
from __future__ import annotations

from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QHBoxLayout, QLabel, QPushButton

from chatport.i18n import t
from chatport.ui import format as fmt
from chatport.ui.pages.base import Context, Page
from chatport.ui.widgets.banner import Banner
from chatport.ui.widgets.progress import ProgressLine
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

        self.notice = Banner("connect.disconnected")
        self.notice.setVisible(False)
        self.body.addWidget(self.notice)
        self.computer_heading = QLabel()
        self.computer_heading.setProperty("role", "heading")
        self.body.addWidget(self.computer_heading)
        self.computer_lines = QLabel()
        self.computer_lines.setWordWrap(True)
        self.body.addWidget(self.computer_lines)

        row = QHBoxLayout()
        row.setSpacing(12)
        self.install_button = QPushButton()
        self.install_button.setProperty("variant", "primary")
        self.install_button.clicked.connect(self.start_job)
        self.install_bar = ProgressLine()
        self.install_bar.set_value(0)
        self.install_label = QLabel()
        self.install_label.setProperty("role", "muted")
        row.addWidget(self.install_button, 0)
        row.addWidget(self.install_bar, 1)
        row.addWidget(self.install_label, 0)
        row.addStretch(1)
        self.body.addLayout(row)
        self._show_install(False)
        self.retranslate()

    # ----- lifecycle ---------------------------------------------------------------------------

    def on_enter(self) -> None:
        self.refresh()
        self.timer.start()

    def on_leave(self) -> None:
        self.notice.setVisible(False)  # the reason for the detour is only relevant while here
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

    def show_notice(self) -> None:
        """Tell the user a phone went away mid-job; stays until the page is left."""
        self.notice.setVisible(True)

    def _on_result(self, result: object) -> None:
        if not isinstance(result, dict):
            return
        self.result = result
        self.ctx.last_connect = result
        self.render()
        self.panels_changed.emit()
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
        self.install_bar.set_value(0)
        self._show_install(True, running=True)
        self.continue_changed.emit(False)
        self.ctx.runner.install_adb()

    def on_event(self, event) -> None:
        if event.kind == "progress":
            self.install_bar.set_value(event.pct)
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
        self.notice.retranslate()
        self.computer_heading.setText(t("connect.computer.title"))
        self.install_button.setText(t("connect.install_adb"))
        self.render()

    def render(self) -> None:
        c = (self.result or {}).get("computer") or {}
        if not self.result:
            self.computer_lines.setText(t("connect.checking"))
            return
        platform = c.get("platform") or {}
        lines = [t("connect.computer.free", free=fmt.bytes_text(c.get("free_bytes")))]
        lines.append(t("connect.computer.adb_ok") if c.get("adb") else t("connect.computer.no_adb"))
        if platform.get("state", "ok") != "ok":
            lines.append(t(f"connect.computer.platform.{platform.get('state')}"))
        self.computer_lines.setText("\n".join(lines))
        if not self._installing:
            self._show_install(not c.get("adb"))
