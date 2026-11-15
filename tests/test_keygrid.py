import pytest

from chatport.core.keygrid import KeyProblem, candidates, find_working_key, normalize

GROUPS = [f"{i:04x}" for i in range(16)]
KEY = "".join(GROUPS)


def test_normalize_strips_separators_and_case():
    text = " ".join(g.upper() for g in GROUPS[:4]) + "-" + ":".join(GROUPS[4:8]) + "." + "|".join(GROUPS[8:])
    assert normalize(text) == KEY
    assert normalize("AB cd\n12\t34") == "abcd1234"


def test_candidates_orderings():
    found = dict(candidates(KEY))
    assert list(found) == ["as_typed", "rows_rtl", "columns", "reversed"]
    assert found["as_typed"] == KEY
    rows = [GROUPS[i:i + 4] for i in range(0, 16, 4)]
    assert found["rows_rtl"] == "".join(g for row in rows for g in reversed(row))
    assert found["columns"] == "".join(rows[r][c] for c in range(4) for r in range(4))
    assert found["reversed"] == "".join(reversed(GROUPS))


def test_candidates_are_unique():
    same = "abcd" * 16
    assert candidates(same) == [("as_typed", same)]


@pytest.mark.parametrize("bad", ["", "abc", KEY[:-1], KEY + "0", "g" * 64])
def test_candidates_reject_bad_format(bad):
    with pytest.raises(KeyProblem) as info:
        candidates(bad)
    assert info.value.code == "key_format"


def test_find_working_key_tries_orderings(tmp_path):
    wanted = bytes.fromhex(dict(candidates(KEY))["columns"])
    tried = []

    def opens(sample, key):
        tried.append(key)
        return key == wanted

    name, key = find_working_key(KEY, tmp_path / "sample", opens)
    assert (name, key) == ("columns", wanted)
    assert len(tried) == 3


def test_find_working_key_wrong(tmp_path):
    with pytest.raises(KeyProblem) as info:
        find_working_key(KEY, tmp_path / "sample", lambda sample, key: False)
    assert info.value.code == "key_wrong"
