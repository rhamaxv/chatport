"""Step 5: the iPhone checklist. Some rows can be verified live, airplane mode is confirmed by hand."""
from __future__ import annotations

import sys

from PySide6.QtWidgets import QHBoxLayout, QLabel, QPushButton

from chatport.i18n import t
from chatport.ui.pages.base import Context, Page
from chatport.ui.widgets.checklist import Checklist
from chatport.ui.workers import FunctionThread


def _os_name() -> str:
    if sys.platform == "darwin":
        return "macos"
    return "windows" if sys.platform.startswith("win") else "linux"


class PreparePage(Page):
    step = "prepare"
    title_key = "prepare.title"
    subtitle_key = "prepare.subtitle"

    def __init__(self, ctx: Context):
        super().__init__(ctx)
        self._thread: FunctionThread | None = None
        self.checklist = Checklist()
        self.checklist.add("whatsapp", "prepare.whatsapp")
        self.checklist.add("find_my", "prepare.find_my")
        self.checklist.add("encryption", f"prepare.encryption.{_os_name()}")
        self.checklist.add("airplane", "prepare.airplane")
        self.checklist.changed.connect(lambda: self.continue_changed.emit(self.can_continue()))
        self.body.addWidget(self.checklist)
        self.track(self.checklist)
        row = QHBoxLayout()
        self.check_button = QPushButton()
        self.check_button.clicked.connect(self.check_iphone)
        self.check_label = QLabel()
        self.check_label.setProperty("role", "muted")
        row.addWidget(self.check_button)
        row.addWidget(self.check_label, 1)
        self.body.addLayout(row)
        self.retranslate()

    def retranslate(self) -> None:
        super().retranslate()
        self.check_button.setText(t("prepare.check"))

    def on_enter(self) -> None:
        self.check_iphone()  # ask the iPhone right away; the user only ticks what cannot be verified
        self.check_label.setText("")

    def on_leave(self) -> None:
        if self._thread is not None and self._thread.isRunning():
            self._thread.wait(5000)

    def can_continue(self) -> bool:
        return self.checklist.all_checked()

    def check_iphone(self) -> None:
        fn = self.ctx.ready_checks_fn
        if fn is None or (self._thread is not None and self._thread.isRunning()):
            return
        self.check_button.setEnabled(False)
        self.check_label.setText(t("prepare.checking"))
        self._thread = FunctionThread(fn, self)
        self._thread.result.connect(self._on_result)
        self._thread.failed.connect(lambda _n: self._on_result({}))
        self._thread.start()

    def _on_result(self, result: object) -> None:
        self.check_button.setEnabled(True)
        iphone = (result or {}).get("iphone") if isinstance(result, dict) else {}
        iphone = iphone or {}
        if iphone.get("state") != "ready":
            self.check_label.setText(t("prepare.no_iphone"))
            return
        whatsapp = iphone.get("whatsapp")
        self.checklist.set_live("whatsapp", True if whatsapp else (None if whatsapp is None else False),
                                None if whatsapp else ("prepare.live.unknown" if whatsapp is None else "prepare.live.whatsapp_missing"))
        find_my = iphone.get("find_my")
        self.checklist.set_live("find_my", None if find_my is None else not find_my,
                                "prepare.live.still_on" if find_my else None)
        encrypted = iphone.get("encrypted")
        self.checklist.set_live("encryption", None if encrypted is None else not encrypted,
                                "prepare.live.still_on" if encrypted else None)
        self.check_label.setText(t("prepare.checked", name=iphone.get("name") or "iPhone"))
        self.continue_changed.emit(self.can_continue())
