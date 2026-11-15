"""Strings. `t("welcome.title")` returns the current language's text, falling back to English, then the key.

Keys are dotted: <page or area>.<name>. Error texts: error.<code>.title, error.<code>.body, error.<code>.action.
Placeholders use str.format: t("copy.bytes", done="1.2 GB", total="4 GB").
"""
from __future__ import annotations

from importlib import import_module

LANGUAGES: tuple[str, ...] = ("en", "id")
_current = "en"
_tables: dict[str, dict[str, str]] = {}


def _table(lang: str) -> dict[str, str]:
    if lang not in _tables:
        _tables[lang] = import_module(f"chatport.i18n.{lang}").STRINGS
    return _tables[lang]


def set_language(lang: str) -> None:
    global _current
    if lang in LANGUAGES:
        _current = lang


def language() -> str:
    return _current


def t(key: str, **kw) -> str:
    text = _table(_current).get(key)
    if text is None and _current != "en":
        text = _table("en").get(key)
    if text is None:
        return key
    try:
        return text.format(**kw) if kw else text
    except (KeyError, IndexError):
        return text


def missing(lang: str) -> list[str]:
    """Keys present in English but not in `lang` (for tests)."""
    return sorted(set(_table("en")) - set(_table(lang)))
