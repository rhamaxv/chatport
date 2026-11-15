import json

from chatport.core.state import State
from chatport.core.steps import STEPS


def test_round_trip(tmp_path):
    path = tmp_path / "state.json"
    state = State(path)
    state.mark("welcome")
    state.mark("connect", android="Pixel")
    state.set_lang("id")

    again = State(path).load()
    assert again.done("welcome") and again.done("connect")
    assert again.get("connect")["android"] == "Pixel"
    assert "at" in again.get("connect")
    assert again.get("key") is None
    assert again.lang == "id"
    assert not (tmp_path / "state.json.tmp").exists()


def test_load_missing_or_broken_file(tmp_path):
    assert State(tmp_path / "none.json").load().current() == "welcome"
    bad = tmp_path / "bad.json"
    bad.write_text("{not json")
    assert State(bad).load().current() == "welcome"


def test_current_is_first_unfinished(tmp_path):
    state = State(tmp_path / "s.json")
    assert state.current() == "welcome"
    for step in STEPS[:2]:
        state.mark(step)
    assert state.current() == "key"
    for step in STEPS[2:-1]:
        state.mark(step)
    assert state.current() == "done"


def test_reset_from_drops_later_steps(tmp_path):
    state = State(tmp_path / "s.json")
    for step in ("welcome", "connect", "key", "copy", "prepare"):
        state.mark(step)
    state.reset_from("key")
    assert state.done("connect")
    assert not state.done("key") and not state.done("copy") and not state.done("prepare")
    assert state.current() == "key"
    state.reset_from("not_a_step")
    assert state.current() == "key"


def test_saved_json_shape(tmp_path):
    path = tmp_path / "s.json"
    State(path).mark("welcome", note=1)
    raw = json.loads(path.read_text())
    assert set(raw) == {"steps", "lang"}
    assert raw["steps"]["welcome"]["note"] == 1
