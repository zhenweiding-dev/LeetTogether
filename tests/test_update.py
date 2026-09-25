"""update.py: the hourly pipeline. Fetchers are fake; the whole run is offline."""

import contextlib
import io
import json

import pytest

import board
import common
import theme
import update
from conftest import (
    CFG,
    NOW,
    PROBLEMS,
    TODAY,
    day_ago,
    detail_for,
    make_history,
    member_record,
    recent_ac,
    sol_all,
)


def run_main():
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf), contextlib.redirect_stderr(buf):
        update.main()
    return buf.getvalue()


# --- sync_questions ----------------------------------------------------------


def user(ok=True, solved_n=10, recent=None, handle="h"):
    return {
        "ok": ok,
        "handle": handle,
        "solved": sol_all(solved_n),
        "recent_ac": recent or [],
    }


def test_sync_questions_fetches_missing_and_stores(paths, fake_lc):
    members = {
        "m1": {"ok": True, "recent_ac": [
            {"slug": "twosum", "title": "Two Sum", "ts": 1},
            {"slug": "fresh", "title": "Fresh", "ts": 2},
        ]},
        "m2": {"ok": False, "error": "x", "recent_ac": []},
    }
    fake_lc.questions["fresh"] = {"frontend_id": "9", "difficulty": "Easy", "tags": ["Array"]}
    common.save_problems(PROBLEMS)

    problems = update.sync_questions(members)

    assert fake_lc.question_calls == ["fresh"]  # twosum already cached
    assert problems["fresh"] == {"frontend_id": "9", "difficulty": "Easy", "tags": ["Array"]}
    assert common.load_problems()["fresh"]["frontend_id"] == "9"


def test_sync_questions_requeries_legacy_string_entries(paths, fake_lc):
    members = {"m1": {"ok": True, "recent_ac": [{"slug": "old", "title": "Old", "ts": 1}]}}
    common.save_problems({"old": "Easy"})  # pre-dict cache shape
    fake_lc.questions["old"] = {"frontend_id": "7", "difficulty": "Easy", "tags": []}
    problems = update.sync_questions(members)
    assert isinstance(problems["old"], dict) and problems["old"]["frontend_id"] == "7"


def test_sync_questions_nothing_missing_is_noop(paths, fake_lc):
    members = {"m1": {"ok": True, "recent_ac": [{"slug": "twosum", "title": "T", "ts": 1}]}}
    common.save_problems(PROBLEMS)
    problems = update.sync_questions(members)
    assert fake_lc.question_calls == []
    assert problems == PROBLEMS


# --- top_up_yesterday --------------------------------------------------------


def test_top_up_raises_yesterday_and_rebuilds_tags(paths):
    cfg = CFG.copy()
    today_json = detail_for({"m1": recent_ac({TODAY: ["twosum"], day_ago(1): ["hardproblem"]})})
    h = make_history({day_ago(1): {
        "m1": member_record(0, sol=sol_all(4)),
        "m2": member_record(1, 1, 0, 0, sol=sol_all(2)),
    }})
    h[day_ago(1)]["tags"] = {"Array": 1}

    update.top_up_yesterday(h, today_json, PROBLEMS, cfg, TODAY)

    m1 = h[day_ago(1)]["members"]["m1"]["day"]
    assert m1 == {"count": 1, "easy": 0, "medium": 0, "hard": 1}  # raised
    assert h[day_ago(1)]["tags"] == {"Graph": 1}  # rebuilt from what was seen


def test_top_up_never_lowers(paths):
    cfg = CFG.copy()
    today_json = detail_for({"m1": recent_ac({day_ago(1): ["twosum"]})})
    h = make_history({day_ago(1): {"m1": member_record(5, 5, 0, 0, sol=sol_all(9))}})
    h[day_ago(1)]["tags"] = {"Array": 3}

    update.top_up_yesterday(h, today_json, PROBLEMS, cfg, TODAY)

    # today's fetch only proves 1 solve for yesterday; the recorded 5 must stay
    assert h[day_ago(1)]["members"]["m1"]["day"]["count"] == 5
    assert h[day_ago(1)]["tags"] == {"Array": 3}  # untouched


def test_top_up_no_yesterday_entry_is_noop(paths):
    h = make_history({day_ago(2): {"m1": member_record(1, sol=sol_all(1))}})
    update.top_up_yesterday(h, detail_for({}), CFG.copy(), PROBLEMS, TODAY)
    assert day_ago(1) not in h


# --- backfill ----------------------------------------------------------------


def test_backfill_fills_missing_days_only(paths):
    h = make_history({
        day_ago(1): {"m1": member_record(1, sol=sol_all(2))},  # group day exists
        day_ago(2): {"m1": member_record(1, sol=sol_all(1))},  # and this one
    })
    members = {
        "m2": {"ok": True, "recent_ac": recent_ac({
            day_ago(1): ["twosum", "medproblem"],
            day_ago(2): ["hardproblem"],
        })},
    }
    update.backfill(h, members, PROBLEMS, CFG.copy(), TODAY)

    assert h[day_ago(1)]["members"]["m2"]["day"] == {"count": 2, "easy": 1, "medium": 1, "hard": 0}
    assert h[day_ago(2)]["members"]["m2"]["day"] == {"count": 1, "easy": 0, "medium": 0, "hard": 1}
    # the group histogram only ever grows for a member who was not in it
    assert h[day_ago(2)]["tags"] == {"Graph": 1}
    assert h[day_ago(1)]["tags"] == {"Array": 1, "Hash Table": 1, "Dynamic Programming": 1}


def test_backfill_never_overwrites_existing(paths):
    h = make_history({day_ago(1): {"m1": member_record(4, sol=sol_all(4))}})
    members = {"m1": {"ok": True, "recent_ac": recent_ac({day_ago(1): ["twosum"]})}}
    update.backfill(h, members, PROBLEMS, CFG.copy(), TODAY)
    assert h[day_ago(1)]["members"]["m1"]["day"]["count"] == 4  # untouched


def test_backfill_skips_today_and_uncovered_days(paths):
    h = make_history({TODAY: {"m1": member_record(0, sol=sol_all(1))}})
    members = {"m2": {"ok": True, "recent_ac": recent_ac({TODAY: ["twosum"]})}}
    update.backfill(h, members, PROBLEMS, CFG.copy(), TODAY)
    assert "m2" not in h[TODAY]["members"]  # today belongs to the normal path


def test_backfill_capped_window_drops_oldest_day(paths):
    # A full recent_ac list is truncated: its oldest day may be missing solves,
    # so that day is excluded rather than recorded as a partial one.
    h = make_history({day_ago(1): {"m1": member_record(0, sol=sol_all(1))},
                      day_ago(2): {"m1": member_record(0, sol=sol_all(1))},
                      day_ago(3): {"m1": member_record(0, sol=sol_all(1))}})
    ac = recent_ac({day_ago(2): [f"p{i}" for i in range(20)],
                    day_ago(3): ["oldest"]})  # 21 items: capped by the API
    members = {"m2": {"ok": True, "recent_ac": ac}}
    update.backfill(h, members, PROBLEMS, CFG.copy(), TODAY)
    assert "m2" not in h[day_ago(3)]["members"]  # partial oldest day excluded
    assert h[day_ago(2)]["members"]["m2"]["day"]["count"] == 20
    assert h[day_ago(1)]["members"]["m2"]["day"]["count"] == 0  # covered, empty


# --- core / mark_run / fetch_members -----------------------------------------


def test_core_only_ok_members():
    m = {"m1": {"ok": True, "solved": sol_all(1), "recent_ac": [1]},
         "m2": {"ok": False, "error": "x", "solved": sol_all(9), "recent_ac": []}}
    assert update.core(m) == {"m1": (sol_all(1), [1])}


def test_mark_run_sets_hour_and_pads():
    fresh = update.mark_run(None, 5)
    assert len(fresh) == 24 and fresh[5] == "1" and fresh.count("1") == 1
    again = update.mark_run({"run_hours": fresh}, 5)
    assert again.count("1") == 1  # same hour twice is one hit
    later = update.mark_run({"run_hours": fresh}, 9)
    assert later[9] == "1" and later.count("1") == 2


def test_fetch_members_ok_and_error_paths(paths, fake_lc, monkeypatch):
    monkeypatch.setattr(update.time, "sleep", lambda s: None)
    cfg = CFG.copy()
    fake_lc.users["alice_lc"] = user(solved_n=5, recent=[{"slug": "twosum", "title": "T", "ts": 1}])
    earlier = {"m1": {"ok": True, "name": "alice", "solved": sol_all(3),
                      "recent_ac": [{"slug": "old", "title": "O", "ts": 1}]}}

    # m1 ok, m2 has no handle, m3's fetch raises
    cfg["members"] = [{"id": "m1", "name": "alice"}, {"id": "m2", "name": "bob"},
                      {"id": "m3", "name": "carol"}]
    handles = {"m1": "alice_lc", "m3": "carol_lc"}

    import lc as lc_mod

    def flaky(handle):
        if handle == "carol_lc":
            raise RuntimeError("boom")
        return fake_lc.users[handle]

    monkeypatch.setattr(lc_mod, "fetch_user", flaky)

    members, failures, kept = update.fetch_members(cfg, handles, earlier)

    assert members["m1"]["ok"] is True and members["m1"]["solved"]["all"] == 5
    assert members["m2"] == {"name": "bob", "ok": False, "error": theme.ERR_NO_HANDLE}
    assert members["m3"]["ok"] is False and members["m3"]["error"] == "boom"
    assert failures == [("m2", theme.ERR_NO_HANDLE), ("m3", "boom")]
    assert kept == []


def test_fetch_members_keeps_earlier_on_blip(paths, fake_lc, monkeypatch):
    monkeypatch.setattr(update.time, "sleep", lambda s: None)
    cfg = {"timezone": "UTC", "score_weights": {"easy": 1, "medium": 3, "hard": 6},
           "members": [{"id": "m1", "name": "alice"}]}
    earlier = {"m1": {"ok": True, "name": "alice", "solved": sol_all(3),
                      "recent_ac": [{"slug": "old", "title": "O", "ts": 1}]}}
    members, failures, kept = update.fetch_members(cfg, {"m1": "alice_lc"}, earlier)
    assert members["m1"]["stale"] is True and members["m1"]["ok"] is True
    assert members["m1"]["solved"]["all"] == 3  # earlier data kept
    assert failures == [] and kept == [("m1", "That user does not exist.")]


# --- preview -----------------------------------------------------------------


def test_preview_rewrites_readme_without_handles(paths, fixed_now, fake_lc, monkeypatch):
    import common as C

    C.README.write_text(f"# Board\n\n{C.MARK_START}\n\nold\n\n{C.MARK_END}\n", encoding="utf-8")
    # data files exist but no handles file and no handles env
    h = make_history({TODAY: {"m1": member_record(2, 1, 1, 0, sol=sol_all(10)),
                              "m2": member_record(1, 1, 0, 0, sol=sol_all(4))}})
    C.save_history({"timezone": "UTC", "score_weights": {}, "fetched_at": "x", "days": h})
    C.save_today(detail_for({}))
    C.save_problems(PROBLEMS)
    C.save_config(CFG)
    monkeypatch.setattr(board, "README", C.README)

    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        update.preview()

    text = C.README.read_text(encoding="utf-8")
    assert "alice" in text and "bob" in text and "old" not in text
    assert fake_lc.user_calls == []  # nothing fetched


def test_preview_no_members_raises(paths, fixed_now):
    C = common
    C.save_config({"timezone": "UTC", "members": []})
    with pytest.raises(SystemExit, match="No members"):
        update.preview()


# --- end-to-end main ---------------------------------------------------------


@pytest.fixture
def repo_state(paths, fixed_now, fake_lc, monkeypatch):
    """A complete fake repo: config, handles, seeded history, fake fetches."""
    monkeypatch.setattr(update.time, "sleep", lambda s: None)
    C = common

    C.save_config(CFG)
    C.save_handles({"m1": "alice_lc", "m2": "bob_lc"})
    C.save_problems(PROBLEMS)
    C.README.write_text(
        f"# Board\n\n{C.MARK_START}\n\nold board\n\n{C.MARK_END}\n", encoding="utf-8"
    )

    # two prior days with totals, so deltas and streaks have something to read
    h = make_history({
        day_ago(2): {
            "m1": member_record(3, 2, 1, 0, sol=sol_all(9), streak=4),
            "m2": member_record(1, 1, 0, 0, sol=sol_all(3), streak=2),
        },
        day_ago(1): {
            # m1's real yesterday solve is only visible through today's fetch,
            # so the stored day starts at zero and gets topped up
            "m1": member_record(0, 0, 0, 0, sol=sol_all(10), streak=5),
            "m2": member_record(1, 1, 0, 0, sol=sol_all(4), streak=3),
        },
    })
    h[day_ago(2)]["tags"] = {"Array": 2}
    h[day_ago(1)]["tags"] = {"Array": 1}
    C.save_history({"timezone": "UTC", "score_weights": {}, "fetched_at": "x", "days": h})

    # today's fetches: m1 solves two (one new problem), m2 solves nothing today
    fake_lc.users["alice_lc"] = user(
        solved_n=12,
        recent=recent_ac({TODAY: ["twosum", "medproblem"], day_ago(1): ["freshhard"]}),
    )
    fake_lc.users["bob_lc"] = user(solved_n=4, recent=recent_ac({day_ago(1): ["twosum"]}))
    fake_lc.questions["freshhard"] = {
        "frontend_id": "4", "difficulty": "Hard", "tags": ["Graph"],
    }
    # update.py renders through board, which holds its own copy of the README
    monkeypatch.setattr(board, "README", C.README)
    return C


def test_main_end_to_end(repo_state):
    run_main()
    C = repo_state

    stored = json.loads(C.HISTORY_PATH.read_text(encoding="utf-8"))
    days = stored["days"]

    # today's record: day counts, run hour, tags
    today = days[TODAY]
    assert today["run_hours"][NOW.hour] == "1"
    assert today["members"]["m1"]["day"] == {"count": 2, "easy": 1, "medium": 1, "hard": 0}
    assert today["members"]["m2"]["day"] == {"count": 0, "easy": 0, "medium": 0, "hard": 0}
    assert today["tags"] == {"Array": 1, "Dynamic Programming": 1, "Hash Table": 1}
    # solved totals land in history as well
    assert today["members"]["m1"]["solved"]["all"] == 12

    # yesterday got topped up: m1's solve is only visible now
    yest = days[day_ago(1)]
    assert yest["members"]["m1"]["day"] == {"count": 1, "easy": 0, "medium": 0, "hard": 1}
    assert yest["tags"] == {"Array": 1, "Graph": 1, "Hash Table": 1}  # both members' solves

    # streaks carried forward: m1 active today -> yesterday's eod 5 + 1
    assert today["members"]["m1"]["streak"] == 6
    assert today["members"]["m2"]["streak"] == 0  # inactive today

    # the new problem's metadata was fetched and cached for tomorrow
    assert json.loads(C.PROBLEMS_PATH.read_text(encoding="utf-8"))["freshhard"]["frontend_id"] == "4"

    # today.json carries the problem lists, nothing else
    tj = json.loads(C.TODAY_PATH.read_text(encoding="utf-8"))
    assert tj["date"] == TODAY and tj["failed"] == {} and tj["stale"] == []
    assert set(tj["members"]) == {"m1", "m2"}
    assert "solved" not in tj["members"]["m1"]

    # README rendered with the board
    text = C.README.read_text(encoding="utf-8")
    assert "alice" in text and "bob" in text and "submitted today" in text


def test_main_second_run_unchanged_preserves_files(repo_state):
    run_main()
    first_stamp = json.loads(repo_state.TODAY_PATH.read_text(encoding="utf-8"))["fetched_at"]
    readme1 = repo_state.README.read_bytes()

    run_main()  # identical fetches -> nothing new

    tj = json.loads(repo_state.TODAY_PATH.read_text(encoding="utf-8"))
    assert tj["fetched_at"] == first_stamp  # kept, not refreshed
    assert repo_state.README.read_bytes() == readme1  # byte-identical


def test_main_requires_handles(repo_state):
    common.HANDLES_PATH.unlink()
    with pytest.raises(SystemExit, match="No LeetCode handles"):
        run_main()