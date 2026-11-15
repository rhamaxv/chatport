"""Runs one engine job at a time on a worker thread and turns its reports into Qt signals."""
from __future__ import annotations

import logging
import threading
import time
from collections.abc import Callable
from pathlib import Path
from typing import Any

from PySide6.QtCore import QObject, QThread, Signal, Slot

from .errors import friendly
from .events import Event
from .keygrid import KeyProblem, candidates, find_working_key
from .state import State

log = logging.getLogger("chatport.jobs")

JobBody = Callable[[Callable[[Event], None]], dict]
AdbInstaller = Callable[[Callable[[int, int], None]], str]

MIN_INTERVAL_S = 1 / 8
# Jobs whose success finishes a wizard step. adb and undo leave the state untouched.
STEP_FOR_JOB = {"key": "key", "copy": "copy", "backup": "backup", "build": "build", "restore": "restore"}
UNCANCELLABLE = ("restore", "undo")


class _Throttle:
    """Lets at most 8 progress events per second through for each (job, phase). Terminal pcts pass."""

    def __init__(self) -> None:
        self._last: dict[tuple[str, str | None], float] = {}

    def allow(self, event: Event) -> bool:
        if event.kind != "progress" or event.pct is None or event.pct >= 100:
            return True
        key = (event.job, event.phase)
        now = time.monotonic()
        if now - self._last.get(key, 0.0) < MIN_INTERVAL_S:
            return False
        self._last[key] = now
        return True


class _Worker(QThread):
    produced = Signal(object)

    def __init__(self, job: str, body: JobBody, parent: QObject | None = None):
        super().__init__(parent)
        self.job, self.body = job, body
        self._throttle = _Throttle()

    def report(self, event: Event) -> None:
        if self._throttle.allow(event):
            self.produced.emit(event)

    def run(self) -> None:
        log.info("job %s started", self.job)
        try:
            result = self.body(self.report)
        except BaseException as exc:  # every failure becomes one error event
            code, data = friendly(exc)
            log.warning("job %s failed: %s %s", self.job, code.value, data.get("detail", ""))
            self.produced.emit(Event(self.job, "error", data={"code": code.value, **data}))
            return
        log.info("job %s finished", self.job)
        self.produced.emit(Event(self.job, "done", data=result))


class JobRunner(QObject):
    event = Signal(object)
    busy_changed = Signal(bool)

    def __init__(self, engine, work_root: Path, state: State, adb_installer: AdbInstaller | None = None,
                 parent: QObject | None = None):
        super().__init__(parent)
        self._engine = engine
        self._work = engine.new_work(Path(work_root))
        self._state = state
        self._adb_installer = adb_installer
        self._lock = threading.Lock()
        self._key: bytes | None = None
        self._cancel = threading.Event()
        self._worker: _Worker | None = None
        self._job: str | None = None

    # ----- queries -----

    def busy(self) -> bool:
        return self._job is not None

    def job_name(self) -> str | None:
        return self._job

    def has_key(self) -> bool:
        return self._key is not None

    def forget_key(self) -> None:
        self._key = None

    def cancel(self) -> None:
        if self._job and self._job not in UNCANCELLABLE:
            self._cancel.set()

    # ----- jobs -----

    def install_adb(self) -> bool:
        if self._adb_installer is None:
            return False
        installer = self._adb_installer

        def body(report: Callable[[Event], None]) -> dict:
            def on_progress(done: int, total: int) -> None:
                pct = 100 * done / total if total else None
                report(Event("adb", "progress", pct=pct, data={"done_bytes": done, "total_bytes": total}))
            return {"path": installer(on_progress)}
        return self._start("adb", body)

    def check_key(self, text: str) -> bool:
        def body(report: Callable[[Event], None]) -> dict:
            candidates(text)
            report(Event("key", "progress", pct=None, phase="sample"))
            sample = self._engine.key_sample(self._work)
            order, key = find_working_key(text, sample, self._engine.key_opens)
            self._key = key
            return {"order": order}
        return self._start("key", body)

    def copy(self) -> bool:
        def body(report: Callable[[Event], None]) -> dict:
            key = self._key
            if key is None:
                raise KeyProblem("key_missing")
            result = dict(self._engine.pull(self._work, report, self._cancel))
            result.update(self._engine.decrypt(self._work, key, report))
            return result
        return self._start("copy", body)

    def backup(self, password: str | None = None) -> bool:
        return self._start("backup", lambda report: self._engine.backup(self._work, report, password))

    def build(self, password: str | None = None) -> bool:
        return self._start("build",
                           lambda report: self._engine.build(self._work, report, self._cancel, password))

    def restore(self, password: str | None = None) -> bool:
        return self._start("restore", lambda report: self._engine.restore(self._work, report, "patched", password))

    def undo(self, password: str | None = None) -> bool:
        return self._start("undo", lambda report: self._engine.restore(self._work, report, "pristine", password))

    # ----- plumbing -----

    def _start(self, job: str, body: JobBody) -> bool:
        with self._lock:
            if self._job is not None:
                return False
            self._job = job
        self._cancel.clear()
        self._retire_worker()
        worker = _Worker(job, body, parent=self)
        worker.produced.connect(self._on_produced)
        self._worker = worker
        self.busy_changed.emit(True)
        worker.start()
        return True

    def _retire_worker(self) -> None:
        if self._worker is not None:
            self._worker.wait()
            self._worker.deleteLater()
            self._worker = None

    @Slot(object)
    def _on_produced(self, event: Event) -> None:
        if event.kind == "done":
            self._mark(event.job, event.data)
        if event.kind in ("done", "error"):
            with self._lock:
                self._job = None
            self.event.emit(event)
            self.busy_changed.emit(False)
            return
        self.event.emit(event)

    def _mark(self, job: str, result: dict[str, Any]) -> None:
        step = STEP_FOR_JOB.get(job)
        if step is None:
            return
        try:
            self._state.mark(step, **result)
        except (OSError, TypeError, ValueError) as exc:
            log.warning("could not save state after %s: %s", job, type(exc).__name__)
