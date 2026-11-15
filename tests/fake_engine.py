"""A scripted stand-in for core.engine.Engine. Each method follows the Script set for its name."""
from __future__ import annotations

import threading
from dataclasses import dataclass, field
from pathlib import Path

from wamove.api import Cancelled

from chatport.core.events import Event


@dataclass
class Script:
    result: dict = field(default_factory=dict)
    raises: BaseException | None = None
    progress: int = 0           # emit this many progress events before finishing
    wait_cancel: bool = False   # block until cancel is set, then raise Cancelled
    phase: str = "fake"


class FakeWork:
    def __init__(self, root: Path):
        self.root = root


class FakeEngine:
    JOB_OF = {"pull": "copy", "decrypt": "copy", "backup": "backup", "build": "build", "restore": "restore"}

    def __init__(self) -> None:
        self.scripts: dict[str, Script] = {}
        self.calls: list[tuple[str, dict]] = []
        self.working_key: bytes | None = None
        self.sample = Path("sample.crypt15")

    def script(self, name: str, **kwargs) -> Script:
        self.scripts[name] = Script(**kwargs)
        return self.scripts[name]

    def _run(self, name: str, report=None, cancel: threading.Event | None = None, job: str | None = None,
             **kwargs) -> dict:
        self.calls.append((name, kwargs))
        script = self.scripts.get(name, Script())
        job = job or self.JOB_OF.get(name, name)
        if report is not None:
            for i in range(script.progress):
                report(Event(job, "progress", pct=100 * (i + 1) / script.progress, phase=script.phase))
        if script.wait_cancel:
            if cancel is None or not cancel.wait(timeout=5):
                raise TimeoutError("test did not cancel")
            raise Cancelled()
        if script.raises is not None:
            raise script.raises
        return dict(script.result)

    # ----- Engine surface -----

    def new_work(self, root: Path) -> FakeWork:
        return FakeWork(root)

    def android_status(self) -> dict:
        return self._run("android_status")

    def iphone_status(self, with_apps: bool = False) -> dict:
        return self._run("iphone_status", with_apps=with_apps)

    def whatsapp_installed(self):
        return self._run("whatsapp_installed").get("installed")

    def key_sample(self, work) -> Path:
        self._run("key_sample")
        return self.sample

    def key_opens(self, sample: Path, key: bytes) -> bool:
        self.calls.append(("key_opens", {"sample": sample}))
        script = self.scripts.get("key_opens")
        if script and script.raises:
            raise script.raises
        return self.working_key is not None and key == self.working_key

    def pull(self, work, report, cancel) -> dict:
        return self._run("pull", report, cancel)

    def decrypt(self, work, key: bytes, report) -> dict:
        return self._run("decrypt", report, key_len=len(key))

    def summary(self, work) -> dict:
        return self._run("summary")

    def backup(self, work, report, password) -> dict:
        return self._run("backup", report, password=password)

    def build(self, work, report, cancel, password) -> dict:
        return self._run("build", report, cancel, password=password)

    def restore(self, work, report, source, password) -> dict:
        return self._run("restore", report, job="restore" if source == "patched" else "undo",
                         source=source, password=password)
