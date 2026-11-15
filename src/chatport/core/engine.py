"""Thin adapter over wamove.api so the rest of the app (and tests) never import wamove directly."""
from __future__ import annotations

import threading
from collections.abc import Callable
from pathlib import Path

from wamove import api
from wamove.cli import Work

from .events import Event

Report = Callable[[Event], None]

# wamove names its build step "prepare"; Chatport calls that job "build".
JOB_NAMES = {"copy": "copy", "backup": "backup", "prepare": "build", "restore": "restore", "undo": "undo"}


def to_event(raw: api.Event) -> Event:
    return Event(job=JOB_NAMES.get(raw.step, raw.step), kind=raw.kind, pct=raw.pct,
                 phase=raw.phase, data=dict(raw.data))


def _bridge(report: Report) -> api.Report:
    return lambda raw: report(to_event(raw))


class Engine:
    def new_work(self, root: Path) -> Work:
        return Work(root)

    def android_status(self) -> dict:
        return api.android_status()

    def iphone_status(self, with_apps: bool = False) -> dict:
        return api.iphone_status(with_apps=with_apps)

    def whatsapp_installed(self) -> bool | None:
        return api.whatsapp_installed()

    def key_sample(self, work: Work) -> Path:
        return api.key_sample(work)

    def key_opens(self, sample: Path, key: bytes) -> bool:
        return api.key_opens(sample, key)

    def pull(self, work: Work, report: Report, cancel: threading.Event) -> dict:
        return api.pull(work, _bridge(report), cancel)

    def decrypt(self, work: Work, key: bytes, report: Report) -> dict:
        return api.decrypt(work, key, _bridge(report))

    def summary(self, work: Work) -> dict:
        return api.summary(work)

    def backup(self, work: Work, report: Report, password: str | None, reuse: bool = False) -> dict:
        return api.backup(work, _bridge(report), password, reuse=reuse)

    def backup_age(self, work: Work, udid: str) -> float | None:
        """Seconds since a full backup of this iPhone was taken into the work folder, or None."""
        return api.backup_age(work, udid)

    def build(self, work: Work, report: Report, cancel: threading.Event, password: str | None) -> dict:
        return api.build(work, _bridge(report), cancel, password)

    def restore(self, work: Work, report: Report, source: str, password: str | None) -> dict:
        return api.restore(work, _bridge(report), source, password)
