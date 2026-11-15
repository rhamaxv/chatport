"""Which wizard steps are finished, saved as JSON so the app can resume where it left off."""
from __future__ import annotations

import json
import os
import threading
import time
from pathlib import Path
from typing import Any

from .steps import STEPS


class State:
    def __init__(self, path: Path):
        self.path = Path(path)
        self._lock = threading.RLock()
        self._steps: dict[str, dict[str, Any]] = {}
        self.lang: str | None = None

    def load(self) -> "State":
        with self._lock:
            try:
                raw = json.loads(self.path.read_text(encoding="utf-8"))
            except (OSError, ValueError):
                raw = {}
            steps = raw.get("steps") if isinstance(raw, dict) else None
            self._steps = {k: dict(v) for k, v in (steps or {}).items() if isinstance(v, dict)}
            lang = raw.get("lang") if isinstance(raw, dict) else None
            self.lang = lang if isinstance(lang, str) else None
        return self

    def save(self) -> None:
        with self._lock:
            payload = json.dumps({"steps": self._steps, "lang": self.lang}, indent=1, default=str)
            self.path.parent.mkdir(parents=True, exist_ok=True)
            tmp = self.path.with_name(self.path.name + ".tmp")
            with open(tmp, "w", encoding="utf-8") as handle:
                handle.write(payload)
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(tmp, self.path)

    def done(self, step: str) -> bool:
        with self._lock:
            return step in self._steps

    def get(self, step: str) -> dict[str, Any] | None:
        with self._lock:
            entry = self._steps.get(step)
            return dict(entry) if entry is not None else None

    def mark(self, step: str, **stats: Any) -> None:
        with self._lock:
            self._steps[step] = {"at": time.time(), **stats}
            self.save()

    def reset_from(self, step: str) -> None:
        """Forget `step` and every later one, so the wizard can redo them."""
        with self._lock:
            if step not in STEPS:
                return
            for later in STEPS[STEPS.index(step):]:
                self._steps.pop(later, None)
            self.save()

    def current(self) -> str:
        with self._lock:
            for step in STEPS:
                if step == "done":
                    break
                if step not in self._steps:
                    return step
            return "done"

    def set_lang(self, lang: str | None) -> None:
        with self._lock:
            self.lang = lang
            self.save()
