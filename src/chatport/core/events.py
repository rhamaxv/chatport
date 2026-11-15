"""Events flowing from engine jobs to the UI. One job ends with exactly one `done` or `error`."""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Literal

Kind = Literal["progress", "need", "clear", "log", "done", "error"]


@dataclass
class Event:
    job: str                      # one of core.steps.JOBS
    kind: Kind
    pct: float | None = None      # 0..100, None = indeterminate
    eta_s: float | None = None
    phase: str | None = None      # engine phase name, e.g. "chats", "WhatsApp Images", "phone", "copy"
    data: dict = field(default_factory=dict)
    # done: result dict from the engine. error: {"code": ErrorCode value, "detail": str, ...}
    # need/clear: {"what": "passcode"}

    def to_dict(self) -> dict:
        return asdict(self)
