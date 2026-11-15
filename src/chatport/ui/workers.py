"""Run a plain function on a QThread and get its result back on the GUI thread."""
from __future__ import annotations

import logging
from collections.abc import Callable

from PySide6.QtCore import QThread, Signal

log = logging.getLogger("chatport.ui")


class FunctionThread(QThread):
    result = Signal(object)
    failed = Signal(str)

    def __init__(self, fn: Callable[[], object], parent=None):
        super().__init__(parent)
        self._fn = fn

    def run(self) -> None:
        try:
            self.result.emit(self._fn())
        except Exception as exc:  # the UI shows a generic message, the log keeps the detail
            log.exception("background check failed")
            self.failed.emit(type(exc).__name__)
