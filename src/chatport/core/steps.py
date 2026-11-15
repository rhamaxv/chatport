"""The wizard's steps, in order. Shared by state, jobs and the UI. Do not rename without updating all."""
from __future__ import annotations

STEPS: tuple[str, ...] = (
    "welcome",   # what happens, what stays safe
    "connect",   # live checks: Android, iPhone, computer
    "key",       # 64-digit backup key, verified against a sample file
    "copy",      # pull + decrypt from Android
    "prepare",   # iPhone checklist: WhatsApp, Find My off, encryption off, airplane mode
    "backup",    # full iPhone backup + WhatsApp-only copy
    "build",     # merge Android chats into the copy, show coverage report
    "restore",   # restore WhatsApp data to the iPhone
    "done",      # verify, undo, delete private copies
)

# Jobs the engine can run. Each emits events with step=<job name>.
JOBS: tuple[str, ...] = ("adb", "key", "copy", "backup", "build", "restore", "undo")
