"""Every error has English text, and t() falls back sensibly."""
from __future__ import annotations

import re

import pytest

from chatport import i18n
from chatport.core.errors import ACTION, ErrorCode
from chatport.i18n import t
from chatport.i18n.en import STRINGS


@pytest.fixture(autouse=True)
def english():
    i18n.set_language("en")
    yield
    i18n.set_language("en")


@pytest.mark.parametrize("code", list(ErrorCode))
def test_every_error_has_title_and_body(code):
    assert STRINGS[f"error.{code.value}.title"]
    assert STRINGS[f"error.{code.value}.body"]
    if ACTION[code] != "none":
        assert STRINGS[f"error.{code.value}.action"]


def test_no_em_dashes_or_empty_strings():
    for key, value in STRINGS.items():
        assert chr(0x2014) not in value, key
        assert value.strip(), key


def test_placeholders_are_balanced():
    for key, value in STRINGS.items():
        assert value.count("{") == value.count("}"), key
        for name in re.findall(r"{(\w+)}", value):
            assert name.isidentifier(), key


def test_t_returns_key_when_missing():
    assert t("does.not.exist") == "does.not.exist"


def test_t_formats_and_ignores_bad_kwargs():
    assert t("header.step", n=2, total=9) == "Step 2 of 9"
    assert t("header.step") == "Step {n} of {total}"
    assert t("header.step", n=2) == "Step {n} of {total}"


def test_indonesian_falls_back_to_english():
    i18n.set_language("id")
    assert i18n.language() == "id"
    assert t("app.name") == "Chatport"
    assert t("error.unknown.title") in (STRINGS["error.unknown.title"], i18n._table("id").get("error.unknown.title"))
    assert t("totally.missing") == "totally.missing"


def test_unknown_language_is_ignored():
    i18n.set_language("fr")
    assert i18n.language() == "en"
