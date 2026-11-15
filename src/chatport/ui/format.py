"""Human readable numbers for the UI: bytes, durations, ages, dates. All text goes through i18n."""
from __future__ import annotations

from datetime import datetime

from chatport.i18n import t


def number(n: int | float | None) -> str:
    if n is None:
        return "0"
    return f"{int(n):,}"


def bytes_text(n: int | float | None) -> str:
    if n is None:
        return ""
    value = float(n)
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if value < 1024 or unit == "TB":
            if unit == "B":
                return f"{int(value)} {unit}"
            return f"{value:.1f} {unit}" if value < 10 else f"{value:.0f} {unit}"
        value /= 1024
    return f"{value:.0f} TB"


def duration(seconds: float | None) -> str:
    if seconds is None or seconds < 0:
        return ""
    s = int(round(seconds))
    if s < 60:
        return t("time.seconds", n=max(s, 1))
    if s < 3600:
        return t("time.minutes", n=s // 60)
    return t("time.hours", h=s // 3600, m=(s % 3600) // 60)


def age(seconds: float | None) -> str:
    if seconds is None:
        return t("time.unknown")
    s = int(seconds)
    if s < 120:
        return t("time.just_now")
    if s < 3600:
        return t("time.minutes_ago", n=s // 60)
    if s < 86400:
        return t("time.hours_ago", n=s // 3600)
    return t("time.days_ago", n=s // 86400)


def date_ms(ms: int | float | None) -> str:
    if not ms:
        return ""
    try:
        return datetime.fromtimestamp(ms / 1000).strftime("%d %b %Y")
    except (OverflowError, OSError, ValueError):
        return ""


def phase(name: str | None) -> str:
    """Engine phase names to text. Unknown names are media folders ("WhatsApp Images")."""
    if not name:
        return t("progress.working")
    key = f"phase.{name.lower()}"
    text = t(key)
    if text != key:
        return text
    return t("phase.folder", name=name.replace("WhatsApp ", ""))
