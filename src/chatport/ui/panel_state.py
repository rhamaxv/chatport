"""What each phone panel shows on a given step: a state word, up to three facts, one status sentence.

Pure functions over the last connect and ready checks, so the window can redraw the panels whenever a
page is entered, a check refreshes, a job starts or stops, or the language changes. When the app resumes
at a later step, the facts fall back to what the Connect step saved.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from chatport.i18n import t
from chatport.ui import format as fmt


@dataclass
class PanelView:
    state: str = "idle"
    facts: list[str] = field(default_factory=list)
    status: str = ""
    dimmed: bool = False


@dataclass
class Situation:
    step: str
    connect: dict
    ready: dict
    saved: dict = field(default_factory=dict)   # the Connect step's saved stats, for a resumed session
    busy: bool = False
    failed: bool = False          # the page is showing an error for its job
    needs_passcode: bool = False
    checklist_done: bool = False


def _android(s: Situation) -> dict:
    a = (s.connect or {}).get("android") or {}
    if a or not s.saved:
        return a
    return {"state": "ready", "model": s.saved.get("android_model")}


def _iphone(s: Situation) -> dict:
    i = (s.ready or {}).get("iphone") or (s.connect or {}).get("iphone") or {}
    if i or not s.saved:
        return i
    return {"state": "ready", "name": s.saved.get("iphone_name"), "find_my": s.saved.get("iphone_find_my"),
            "encrypted": s.saved.get("iphone_encrypted")}


def _android_facts(a: dict) -> list[str]:
    facts = []
    if a.get("model"):
        facts.append(str(a["model"]))
    if a.get("backup") == "ok":
        facts.append(t("panel.fact.backup", age=fmt.age(a.get("backup_age_s"))))
    return facts


def _iphone_facts(i: dict) -> list[str]:
    facts = []
    if i.get("name"):
        facts.append(str(i["name"]))
    if i.get("ios"):
        facts.append(t("panel.fact.ios", ios=i["ios"]))
    if i.get("used_bytes"):
        facts.append(t("panel.fact.used", used=fmt.bytes_text(i["used_bytes"])))
    if i.get("find_my"):
        facts.append(t("panel.fact.find_my_on"))
    if i.get("encrypted"):
        facts.append(t("panel.fact.encrypted"))
    return facts[:3]


def _android_connect(a: dict) -> PanelView:
    if not a:
        return PanelView("waiting", [], t("panel.checking"))
    state = a.get("state", "missing")
    if state == "ready":
        backup = a.get("backup", "none")
        if backup == "ok":
            return PanelView("ready", _android_facts(a), t("connect.android.ready", model=a.get("model") or "Android"))
        return PanelView("needs_you", _android_facts(a), t(f"connect.android.backup.{backup}") + "\n" + t("key.howto.path"))
    return PanelView("needs_you", [], t(f"connect.android.{state}"))


def _iphone_connect(i: dict) -> PanelView:
    if not i:
        return PanelView("waiting", [], t("panel.checking"))
    state = i.get("state", "missing")
    if state == "ready":
        notes = []
        if i.get("encrypted"):
            notes.append(t("connect.iphone.encrypted"))
        if i.get("find_my"):
            notes.append(t("connect.iphone.find_my"))
        return PanelView("ready", _iphone_facts(i), "\n".join(notes) or t("connect.iphone.ready", name=i.get("name") or "iPhone", ios=i.get("ios") or ""))
    return PanelView("needs_you", [], t(f"connect.iphone.{state}"))


def android_view(s: Situation) -> PanelView:
    a = _android(s)
    facts = _android_facts(a)
    if s.step == "connect":
        return _android_connect(a)
    if s.step == "key":
        return PanelView("ready" if a.get("state") == "ready" else "waiting", facts, t("panel.android.key"))
    if s.step == "copy":
        if s.failed:
            return PanelView("needs_you", facts, t("panel.android.copy"))
        return PanelView("waiting" if s.busy else "ready", facts, t("panel.android.copy" if s.busy else "panel.android.copied"))
    if s.step in ("prepare", "backup", "build", "restore"):
        return PanelView("idle", facts, t("panel.android.rest"), dimmed=True)
    if s.step == "done":
        return PanelView("moved", facts, t("panel.android.moved"))
    return PanelView("idle", facts, "", dimmed=True)


def iphone_view(s: Situation) -> PanelView:
    i = _iphone(s)
    facts = _iphone_facts(i)
    if s.step == "connect":
        return _iphone_connect(i)
    if s.step in ("key", "copy"):
        return PanelView("idle", facts, t("panel.iphone.rest"), dimmed=True)
    if s.step == "prepare":
        if s.checklist_done:
            return PanelView("ready", facts, t("panel.iphone.prepared"))
        return PanelView("needs_you", facts, t("panel.iphone.prepare"))
    if s.step == "backup":
        if s.needs_passcode:
            return PanelView("needs_you", facts, t("backup.banner"))
        if s.failed:
            return PanelView("needs_you", facts, t("panel.iphone.backup"))
        return PanelView("waiting" if s.busy else "ready", facts, t("panel.iphone.backup" if s.busy else "panel.iphone.backed_up"))
    if s.step == "build":
        return PanelView("idle", facts, t("panel.iphone.build"), dimmed=True)
    if s.step == "restore":
        if s.needs_passcode:
            return PanelView("needs_you", facts, t("backup.banner"))
        if s.failed:
            return PanelView("needs_you", facts, t("panel.iphone.backup"))
        return PanelView("waiting" if s.busy else "ready", facts, t("panel.iphone.restoring" if s.busy else "panel.iphone.restore"))
    if s.step == "done":
        return PanelView("received", facts, t("panel.iphone.received"))
    return PanelView("idle", facts, "", dimmed=True)
