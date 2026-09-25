"""common.py: config/handles/data IO, timezone math, cache accessors."""

import json

import common
from conftest import CFG, PROBLEMS, TODAY, day_ago, write_json


def test_load_config_defaults(paths):
    write_json(paths / "config_path.json", {"members": []})
    cfg = common.load_config()
    assert cfg["timezone"] == "UTC"  # default when absent
    assert cfg["score_weights"] == {"easy": 1, "medium": 3, "hard": 6}


def test_load_config_keeps_explicit(paths):
    explicit = {"timezone": "Asia/Tokyo", "score_weights": {"easy": 2},
                "members": [{"id": "m1", "name": "x"}]}
    write_json(paths / "config_path.json", explicit)
    cfg = common.load_config()
    assert cfg["timezone"] == "Asia/Tokyo"
    assert cfg["score_weights"] == {"easy": 2}


def test_save_config_roundtrip(paths):
    common.save_config(CFG)
    with open(paths / "config_path.json", encoding="utf-8") as f:
        assert json.load(f) == CFG


def test_load_handles_env_wins(paths, monkeypatch):
    write_json(paths / "handles_path.json", {"m1": "fromfile"})
    monkeypatch.setenv(common.HANDLES_ENV, json.dumps({"m1": "fromenv"}))
    assert common.load_handles() == {"m1": "fromenv"}


def test_load_handles_empty_env_falls_back_to_file(paths, monkeypatch):
    write_json(paths / "handles_path.json", {"m1": "fromfile"})
    monkeypatch.setenv(common.HANDLES_ENV, "   ")
    assert common.load_handles() == {"m1": "fromfile"}


def test_load_handles_nothing(paths):
    assert common.load_handles() == {}


def test_save_handles_sorted(paths):
    common.save_handles({"m2": "zoe", "m1": "amy"})
    text = (paths / "handles_path.json").read_text(encoding="utf-8")
    assert text.index("amy") < text.index("zoe")  # sorted keys


def test_days_back_window_ascending():
    got = common.days_back(TODAY, 3)
    assert got == [day_ago(2), day_ago(1), TODAY]


def test_days_back_negative_n():
    assert common.days_back(TODAY, 0) == []


def test_local_date_converts_into_cfg_tz():
    # 2026-09-25 01:00 UTC is 2026-09-24 in America/Los_Angeles (UTC-7, PDT).
    cfg = {"timezone": "America/Los_Angeles"}
    import datetime

    ts = int(datetime.datetime(2026, 9, 25, 1, 0, tzinfo=datetime.timezone.utc).timestamp())
    assert common.local_date(ts, cfg) == "2026-09-24"


def test_difficulty_of_dict_and_legacy_string():
    assert common.difficulty_of(PROBLEMS, "twosum") == "Easy"
    legacy = {"twosum": "Easy"}  # older caches stored the bare string
    assert common.difficulty_of(legacy, "twosum") == "Easy"
    assert common.difficulty_of({}, "missing") == ""


def test_frontend_id_of_dict_and_legacy():
    assert common.frontend_id_of(PROBLEMS, "twosum") == "1"
    assert common.frontend_id_of({"twosum": "Easy"}, "twosum") == ""  # legacy: no id
    assert common.frontend_id_of({}, "nope") == ""


def test_tags_of_dict_and_legacy():
    assert common.tags_of(PROBLEMS, "twosum") == ["Array", "Hash Table"]
    assert common.tags_of(PROBLEMS, "medproblem") == ["Dynamic Programming"]
    assert common.tags_of({"twosum": "Easy"}, "twosum") == []
    assert common.tags_of({}, "nope") == []


def test_problems_roundtrip(paths):
    common.save_problems(PROBLEMS)
    assert common.load_problems() == PROBLEMS


def test_read_missing_history(paths):
    data, bad = common.load_history()
    assert data == {} and bad is None


def test_read_broken_history_flagged(paths):
    (paths / "history_path.json").write_text("{not json", encoding="utf-8")
    data, bad = common.load_history()
    assert data == {} and bad == "history_path.json"


def test_history_roundtrip(paths):
    stored = {"timezone": "UTC", "score_weights": {}, "fetched_at": "x", "days": {TODAY: {"run_hours": "1", "members": {}}}}
    common.save_history(stored)
    data, bad = common.load_history()
    assert data == stored and bad is None


def test_today_roundtrip_and_broken(paths):
    common.save_today({"date": TODAY, "members": {}, "failed": {}, "stale": []})
    assert common.load_today()[0]["date"] == TODAY
    (paths / "today_path.json").write_text("[]", encoding="utf-8")  # valid JSON, wrong shape
    data, bad = common.load_today()
    assert data == [] and bad is None  # _read only guards JSONDecodeError


def test_readme_writes_via_path(paths):
    common.README.write_text("hi", encoding="utf-8")
    assert common.README.read_text(encoding="utf-8") == "hi"