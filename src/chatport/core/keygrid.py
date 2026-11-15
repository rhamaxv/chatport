"""The 64-digit backup key as users type it from a 4 x 4 grid of 4-digit groups.

Phones with a right-to-left interface may show the groups mirrored, so the same key can be read
in several orders. We try each plausible order against a small sample file before copying anything.
"""
from __future__ import annotations

import re
from collections.abc import Callable
from pathlib import Path

GROUP = 4
PER_ROW = 4
GROUPS = 16
HEX64 = re.compile(r"^[0-9a-f]{64}$")
_SEPARATORS = re.compile(r"[\s\-:.|]+")


class KeyProblem(Exception):
    def __init__(self, code: str):
        super().__init__(code)
        self.code = code


def normalize(text: str) -> str:
    return _SEPARATORS.sub("", text).lower()


def _groups(hex64: str) -> list[str]:
    return [hex64[i:i + GROUP] for i in range(0, len(hex64), GROUP)]


def _rows(groups: list[str]) -> list[list[str]]:
    return [groups[i:i + PER_ROW] for i in range(0, GROUPS, PER_ROW)]


def _orderings(hex64: str) -> list[tuple[str, str]]:
    groups = _groups(hex64)
    rows = _rows(groups)
    rows_rtl = [g for row in rows for g in reversed(row)]
    columns = [rows[r][c] for c in range(PER_ROW) for r in range(len(rows))]
    return [
        ("as_typed", hex64),
        ("rows_rtl", "".join(rows_rtl)),
        ("columns", "".join(columns)),
        ("reversed", "".join(reversed(groups))),
    ]


def candidates(text: str) -> list[tuple[str, str]]:
    """Unique key orderings worth trying, most likely first. Raises KeyProblem("key_format")."""
    hex64 = normalize(text)
    if not HEX64.match(hex64):
        raise KeyProblem("key_format")
    seen: set[str] = set()
    unique = []
    for name, value in _orderings(hex64):
        if value not in seen:
            seen.add(value)
            unique.append((name, value))
    return unique


def find_working_key(text: str, sample: Path, opens: Callable[[Path, bytes], bool]) -> tuple[str, bytes]:
    """Try each ordering against the sample file. Raises KeyProblem("key_wrong") if none opens it."""
    for name, value in candidates(text):
        key = bytes.fromhex(value)
        if opens(sample, key):
            return name, key
    raise KeyProblem("key_wrong")
