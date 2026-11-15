"""A JobRunner stand-in that plays scripted events on timers, so the UI runs without any phone."""
from __future__ import annotations

import time

from PySide6.QtCore import QObject, QTimer, Signal

from chatport.core.events import Event

NOW_MS = int(time.time() * 1000)

RESULTS: dict[str, dict] = {
    "adb": {"path": "/tmp/platform-tools/adb"},
    "key": {"order": "as_typed"},
    "copy": {"chats": 142, "groups": 23, "messages": 61204, "media": 8311, "contacts": 388,
             "media_bytes": 3_900_000_000, "first_ms": NOW_MS - 4 * 365 * 86400 * 1000, "last_ms": NOW_MS - 3600 * 1000},
    "backup": {"entries": 1200, "encrypted": False, "used_bytes": 21_000_000_000},
    "build": {"chats_created": 119, "chats_merged": 23, "messages_added": 61204, "media_found": 8290,
              "media_missing": 21,
              "coverage": {"skipped": {"revoked": 310, "system": 1250},
                           "unconverted_tables": {"message_add_on_reaction": 4000, "call_log": 120}}},
    "restore": {"used_bytes_before": 21_000_000_000},
    "undo": {"used_bytes_before": 25_000_000_000},
}

PHASES: dict[str, list[tuple[str, float | None]]] = {
    "adb": [("download", 20.0), ("download", 70.0)],
    "key": [("check", None)],
    "copy": [("chats", 5.0), ("WhatsApp Images", 40.0), ("WhatsApp Video", 80.0), ("decrypt", None), ("read", None)],
    "backup": [("phone", 15.0), ("phone", 60.0), ("copy", None)],
    "build": [("read", 5.0), ("chats", 45.0), ("media", 80.0), ("check", 95.0)],
    "restore": [("phone", 20.0), ("phone", 75.0)],
    "undo": [("phone", 30.0), ("phone", 80.0)],
}


class FakeRunner(QObject):
    event = Signal(object)
    busy_changed = Signal(bool)

    def __init__(self, interval_ms: int = 30, parent=None):
        super().__init__(parent)
        self.interval_ms = interval_ms
        self.script: dict[str, str | dict] = {}
        self.calls: list[tuple] = []
        self._job: str | None = None
        self._key_known = False
        self._timers: list[QTimer] = []

    # ----- JobRunner surface --------------------------------------------------------------------

    def install_adb(self) -> None:
        self._start("adb")

    def check_key(self, text: str) -> None:
        self._key_known = True
        self._start("key", len(text))

    def copy(self) -> None:
        self._start("copy")

    def backup(self, password: str | None) -> None:
        self._start("backup", password is not None)

    def build(self, password: str | None) -> None:
        self._start("build")

    def restore(self, password: str | None) -> None:
        self._start("restore")

    def undo(self, password: str | None) -> None:
        self._start("undo")

    def cancel(self) -> None:
        if self._job is None:
            return
        for timer in self._timers:
            timer.stop()
        self._timers.clear()
        job = self._job
        QTimer.singleShot(self.interval_ms, lambda: self._end(job, Event(job, "error", data={"code": "cancelled"})))

    def busy(self) -> bool:
        return self._job is not None

    def job_name(self) -> str | None:
        return self._job

    def has_key(self) -> bool:
        return self._key_known

    def forget_key(self) -> None:
        self._key_known = False

    # ----- scripting ----------------------------------------------------------------------------

    def _start(self, job: str, *args) -> None:
        if self._job is not None:
            raise RuntimeError(f"fake runner busy with {self._job}")
        self._job = job
        self.calls.append((job, *args))
        self.busy_changed.emit(True)
        events: list[Event] = []
        total = 10_000_000 if job == "copy" else None
        for phase, pct in PHASES.get(job, []):
            data = {"done_bytes": int(total * (pct or 0) / 100), "total_bytes": total} if total and pct else {}
            events.append(Event(job, "progress", pct=pct, eta_s=None if pct is None else (100 - pct) * 2, phase=phase, data=data))
        if job in ("backup", "restore"):
            events.insert(1, Event(job, "need", data={"what": "passcode"}))
            events.insert(3, Event(job, "clear", data={"what": "passcode"}))
        outcome = self.script.get(job, "ok")
        if outcome == "ok":
            final = Event(job, "done", pct=100, data=dict(RESULTS.get(job, {})))
        elif isinstance(outcome, dict):
            final = Event(job, "error", data=dict(outcome))
        else:
            final = Event(job, "error", data={"code": str(outcome), "detail": f"fake {outcome}"})
        for i, ev in enumerate(events):
            self._later((i + 1) * self.interval_ms, ev)
        self._later((len(events) + 1) * self.interval_ms, final, terminal=True)

    def _later(self, ms: int, ev: Event, terminal: bool = False) -> None:
        timer = QTimer(self)
        timer.setSingleShot(True)
        timer.timeout.connect(lambda: self._end(ev.job, ev) if terminal else self._emit(ev.job, ev))
        self._timers.append(timer)
        timer.start(ms)

    def _emit(self, job: str, ev: Event) -> None:
        if self._job == job:
            self.event.emit(ev)

    def _end(self, job: str, ev: Event) -> None:
        if self._job != job:
            return
        self._job = None
        self._timers.clear()
        self.event.emit(ev)
        self.busy_changed.emit(False)


def fake_checks() -> dict:
    return {
        "android": {"state": "ready", "model": "Pixel 7", "backup": "ok", "backup_age_s": 1900},
        "iphone": {"state": "ready", "name": "Rizky's iPhone", "ios": "17.5", "used_bytes": 21_000_000_000,
                   "find_my": False, "encrypted": False},
        "computer": {"free_bytes": 180_000_000_000, "adb": "/usr/local/bin/adb",
                     "platform": {"state": "ok", "detail": "", "os": "macos"}},
    }


def fake_checks_missing() -> dict:
    return {
        "android": {"state": "missing"},
        "iphone": {"state": "untrusted"},
        "computer": {"free_bytes": 180_000_000_000, "adb": None,
                     "platform": {"state": "ok", "detail": "", "os": "macos"}},
    }


def fake_ready_checks() -> dict:
    result = fake_checks()
    result["iphone"]["whatsapp"] = True
    return {"iphone": result["iphone"]}
