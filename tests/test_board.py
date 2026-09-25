"""board.py: the metrics and the renderer. All offline, all deterministic.

Streaks, solved deltas, window sums, the run-rate estimator and the rendered
tables are the parts that would silently go wrong after a data-format tweak, so
they get the most attention. `board.local_now` is pinned to NOW so the "today"
every function builds on is fixed.
"""

from collections import Counter

import pytest

import board
import theme
from conftest import (
    CFG,
    PROBLEMS,
    TODAY,
    day_ago,
    detail_for,
    make_history,
    member_record,
    recent_ac,
    sol_all,
    solved,
    ts,
)


def dcfg(**kw):
    cfg = {k: v for k, v in CFG.items()}
    cfg.update(kw)
    return cfg


# --- day_events / day_counts / tag_histogram ---------------------------------


def test_day_events_filters_to_date_and_dedupes():
    detail = detail_for(
        {"m1": recent_ac({TODAY: ["twosum", "twosum"], day_ago(1): ["medproblem"]})}
    )
    ev = board.day_events("m1", detail, dcfg(), TODAY)
    assert list(ev) == ["twosum"]  # same problem twice in one day counts once


def test_day_events_keeps_earliest_of_duplicates():
    detail = detail_for(
        {"m1": [
            {"slug": "twosum", "title": "Two Sum", "ts": ts(TODAY, 12)},
            {"slug": "twosum", "title": "Two Sum", "ts": ts(TODAY, 9)},
        ]}
    )
    ev = board.day_events("m1", detail, dcfg(), TODAY)
    assert ev["twosum"]["ts"] == ts(TODAY, 9)  # earliest wins


def test_day_events_missing_member_is_empty():
    assert board.day_events("m9", detail_for({}), dcfg(), TODAY) == {}


def test_day_counts_splits_difficulty():
    counts = board.day_counts(["twosum", "medproblem", "hardproblem", "twosum"], PROBLEMS)
    assert counts == {"count": 4, "easy": 2, "medium": 1, "hard": 1}


def test_day_counts_unknown_difficulty_counts_but_no_bucket():
    counts = board.day_counts(["nope"], {"nope": {"difficulty": "", "tags": []}})
    assert counts == {"count": 1, "easy": 0, "medium": 0, "hard": 0}


def test_tag_histogram_sorted_and_merged():
    h = board.tag_histogram(["twosum", "twosum", "medproblem"], PROBLEMS)
    assert h == {"Array": 2, "Hash Table": 2, "Dynamic Programming": 1}


# --- member_days / day_stats / day_count -------------------------------------


def test_member_days_only_that_member_ascending():
    h = make_history({day_ago(1): {"m1": member_record(1), "m2": member_record(5)},
                      TODAY: {"m1": member_record(2)}})
    assert list(board.member_days(h, "m1")) == [day_ago(1), TODAY]


def test_day_stats_skips_missing_day_field():
    days = {"2026-09-24": {"day": {"count": 1}}, "2026-09-25": {"run_hours": "x"}}
    assert board.day_stats(days) == {"2026-09-24": {"count": 1}}


def test_day_count_none_when_absent():
    days = {TODAY: member_record(3)["day"]}
    assert board.day_count(TODAY, days) == 3
    assert board.day_count(day_ago(3), days) is None  # no data != zero


# --- streaks -----------------------------------------------------------------


def streak_from(history, mid="m1", today=TODAY):
    days = board.day_stats(board.member_days(history, mid))
    return board.streak_of(days, today)


def test_streak_simple():
    h = make_history({TODAY: {"m1": member_record(2, sol=sol_all(10))},
                      day_ago(1): {"m1": member_record(1, sol=sol_all(9))},
                      day_ago(2): {"m1": member_record(1, sol=sol_all(8))},
                      day_ago(3): {"m1": member_record(0, sol=sol_all(8))}})
    assert streak_from(h) == (3, False)  # the zero day is a confirmed break


def test_streak_not_submitted_today_is_not_a_break():
    h = make_history({TODAY: {"m1": member_record(0, sol=sol_all(8))},
                      day_ago(1): {"m1": member_record(1, sol=sol_all(8))},
                      day_ago(2): {"m1": member_record(1, sol=sol_all(7))},
                      day_ago(3): {"m1": member_record(0, sol=sol_all(7))}})
    assert streak_from(h) == (2, False)  # anchored on yesterday


def test_streak_break_is_confirmed():
    h = make_history({TODAY: {"m1": member_record(1, sol=sol_all(12))},
                      day_ago(1): {"m1": member_record(0, sol=sol_all(11))},
                      day_ago(2): {"m1": member_record(1, sol=sol_all(11))},
                      day_ago(3): {"m1": member_record(1, sol=sol_all(10))}})
    assert streak_from(h) == (1, False)  # a zero day is a real break


def test_streak_zero_when_nothing_submitted():
    h = make_history({TODAY: {"m1": member_record(0, sol=sol_all(1))},
                      day_ago(1): {"m1": member_record(0, sol=sol_all(1))}})
    assert streak_from(h) == (0, False)


def test_streak_window_limited():
    # 14 consecutive solve-days ending today, then the window runs out: the real
    # streak may be longer, so it must say "limited", not a confirmed count.
    dates = [TODAY] + [day_ago(n) for n in range(1, 14)]
    h = make_history({d: {"m1": member_record(1, sol=sol_all(30 - i))}
                      for i, d in enumerate(dates)})
    got, limited = streak_from(h)
    assert got == 14 and limited is True


def test_stored_streak_reads_yesterday():
    h = make_history({day_ago(1): {"m1": member_record(1, streak=12)}})
    days = board.member_days(h, "m1")
    assert board.stored_streak(days, TODAY) == 12
    assert board.stored_streak(days, day_ago(5)) is None


def test_streak_with_history_carries_forward():
    days = board.day_stats({TODAY: member_record(1), day_ago(1): member_record(1)})
    display, eod, limited = board.streak_with_history(days, TODAY, active=True, prev_eod=20)
    assert display == 21 and eod == 21 and limited is False


def test_streak_with_history_inactive_zeroes_eod():
    days = board.day_stats({TODAY: member_record(0), day_ago(1): member_record(1)})
    display, eod, limited = board.streak_with_history(days, TODAY, active=False, prev_eod=20)
    assert display == 20 and eod == 0


def test_streak_with_history_floor_from_derived():
    # Stored count stale-low; the window proves more.
    days = board.day_stats({TODAY: member_record(1), day_ago(1): member_record(1)})
    display, eod, _ = board.streak_with_history(days, TODAY, active=True, prev_eod=1)
    assert display == 2


# --- solved_deltas -----------------------------------------------------------


def test_solved_deltas_per_difficulty():
    h = make_history({
        day_ago(2): {"m1": member_record(1, sol=solved(10, 4, 5, 1))},
        day_ago(1): {"m1": member_record(1, sol=solved(12, 5, 6, 1))},
        TODAY: {"m1": member_record(1, sol=solved(15, 6, 7, 2))},
    })
    deltas = board.solved_deltas(board.member_days(h, "m1"))
    assert deltas[day_ago(1)] == {"easy": 1, "medium": 1, "hard": 0}
    assert deltas[TODAY] == {"easy": 1, "medium": 1, "hard": 1}


def test_solved_deltas_skips_day_only_records_without_reset():
    # A backfilled record (no `solved`) must not break the chain: the jump the
    # next real totals show lands on that day, not the backfilled one.
    h = make_history({
        day_ago(2): {"m1": member_record(1, sol=solved(10, 4, 5, 1))},
        day_ago(1): {"m1": member_record(1)},  # backfilled: day counts only
        TODAY: {"m1": member_record(1, sol=solved(13, 5, 7, 1))},
    })
    deltas = board.solved_deltas(board.member_days(h, "m1"))
    assert deltas[TODAY] == {"easy": 1, "medium": 2, "hard": 0}
    assert day_ago(1) not in deltas


def test_solved_deltas_clamps_shrinkage():
    h = make_history({
        day_ago(1): {"m1": member_record(1, sol=solved(10, 4, 5, 1))},
        TODAY: {"m1": member_record(1, sol=solved(9, 3, 5, 1))},  # totals went down
    })
    deltas = board.solved_deltas(board.member_days(h, "m1"))
    assert deltas[TODAY] == {"easy": 0, "medium": 0, "hard": 0}


# --- window_stats ------------------------------------------------------------


def ws(dates, days, deltas):
    return board.window_stats(dates, days, CFG["score_weights"], deltas)


def test_window_stats_plain():
    days = {TODAY: {"count": 3, "easy": 1, "medium": 1, "hard": 1}}
    assert ws([TODAY], days, {}) == (3, 1 + 3 + 6, False)


def test_window_stats_partial_when_day_missing():
    days = {TODAY: {"count": 3, "easy": 2, "medium": 1, "hard": 0}}
    assert ws([day_ago(1), TODAY], days, {}) == (3, 5, True)


def test_window_stats_capped_day_reads_deltas():
    # 20+ solves truncates the fetch window; the lifetime totals prove the day.
    days = {TODAY: {"count": 20, "easy": 10, "medium": 10, "hard": 0}}
    deltas = {TODAY: {"easy": 11, "medium": 12, "hard": 1}}
    probs, pts, partial = ws([TODAY], days, deltas)
    assert (probs, pts, partial) == (11 + 12 + 1, 11 + 36 + 6, False)


def test_window_stats_capped_day_without_deltas_partial():
    days = {TODAY: {"count": 20, "easy": 10, "medium": 10, "hard": 0}}
    probs, pts, partial = ws([TODAY], days, {})
    assert (probs, pts, partial) == (20, 40, True)


def test_window_stats_missing_weights_key_is_zero():
    days = {TODAY: {"count": 1, "easy": 1, "medium": 0, "hard": 0}}
    probs, pts, _ = board.window_stats([TODAY], days, {"easy": 1}, {})
    assert pts == 1


# --- window_tags / window_diffs / ranked -------------------------------------


def test_window_tags_sums_group():
    h = make_history({TODAY: {"m1": member_record(1)},
                      day_ago(1): {"m1": member_record(1)}})
    h[TODAY]["tags"] = {"Array": 2}
    h[day_ago(1)]["tags"] = {"Array": 1, "Graph": 1}
    assert board.window_tags([day_ago(1), TODAY], h) == {"Array": 3, "Graph": 1}


def test_window_diffs_sums_member_days():
    days = {TODAY: {"count": 2, "easy": 1, "medium": 1, "hard": 0},
            day_ago(1): {"count": 1, "easy": 0, "medium": 1, "hard": 0}}
    assert board.window_diffs([day_ago(1), TODAY], days) == {"easy": 1, "medium": 2, "hard": 0}


def test_ranked_by_count_then_name():
    assert board.ranked(Counter({"b": 2, "a": 2, "c": 1})) == [("a", 2), ("b", 2), ("c", 1)]


# --- small render helpers ----------------------------------------------------


def test_num_partial_prefix():
    assert board.num(5, False) == "5"
    assert board.num(5, True) == "≥5"


def test_esc_and_code():
    assert board.esc('a&"b') == "a&amp;&quot;b"
    assert board.code("x") == "<code>x</code>"


def test_tag_chips():
    assert board.tag_chips([("Array", 3), ("DP tag", 1)]) == (
        "<code>Array丨3</code> <code>DP tag丨1</code>"
    )


def test_diff_line_orders_easy_medium_hard():
    line = board.diff_line({"hard": 1, "easy": 2})
    assert "Easy 2" in line and "Hard 1" in line
    assert line.index("Easy") < line.index("Hard")


def test_tag_line_bare_below_min_count():
    line = board.tag_line([("Array", 5), ("Rare", 1)])
    assert "Array丨5" in line and "Rare" in line and "Rare丨1" not in line


def test_streak_ladder_matches_levels():
    ladder = board.streak_ladder()
    rungs = ladder.split(theme.LADDER_JOIN)
    assert rungs[0].startswith(theme.STREAK_LEVELS[0][1])
    assert rungs[-1].startswith(theme.STREAK_LEVELS[-1][1])


def test_progress_icon_thresholds():
    assert board.progress_icon(3, 3) == "🎉"
    assert board.progress_icon(2, 3) == "🔥"
    assert board.progress_icon(0, 3) == "💤"  # nobody -> distinct glyph
    assert board.progress_icon(0, 0) == "💤"


def test_table_structure_and_footer():
    out = board.table(["A", "B"], ["left", "center"], [["x", "y"]], footer="foot")
    assert "<table>" in out and "<thead>" in out and "<tbody>" in out
    assert '<td colspan="2">foot</td>' in out
    assert 'align="center"' in out


def test_table_header_widths():
    out = board.table(["A", "B"], ["left", "left"], [], widths=["15%", "55%"])
    assert 'width="15%"' in out and 'width="55%"' in out


def test_table_mismatched_headers_aligns_raises():
    with pytest.raises(ValueError, match="differ"):
        board.table(["A", "B"], ["left"], [])


# --- build_rows / ranking ----------------------------------------------------


def test_build_rows_sort_scores_above_counts():
    h = make_history({
        TODAY: {
            "m1": member_record(4, 4, 0, 0, sol=sol_all(12)),  # 4 easy = 4 pts
            "m2": member_record(1, 0, 1, 0, sol=sol_all(6)),   # 1 med = 3 pts
        },
        day_ago(1): {"m1": member_record(1, sol=sol_all(10)), "m2": member_record(1, sol=sol_all(5))},
    })
    rows, broken = board.build_rows(dcfg(), h, detail_for({}), PROBLEMS, TODAY)
    assert [r["id"] for r in rows] == ["m1", "m2"]  # weighted points, not count
    assert broken == []


def test_build_rows_tiebreak_week_then_streak():
    h = make_history({
        TODAY: {"m1": member_record(0, sol=sol_all(5)), "m2": member_record(0, sol=sol_all(5))},
        day_ago(1): {"m1": member_record(1, sol=sol_all(5)), "m2": member_record(1, sol=sol_all(5))},
        day_ago(2): {"m1": member_record(1, sol=sol_all(5))},  # m1 has the longer streak
    })
    rows, _ = board.build_rows(dcfg(), h, detail_for({}), PROBLEMS, TODAY)
    assert rows[0]["id"] == "m1"


def test_build_rows_broken_member_out_of_ranking():
    h = make_history({TODAY: {"m1": member_record(1, sol=sol_all(1))}})
    detail = detail_for({}, failed={"m2": "boom"})
    rows, broken = board.build_rows(dcfg(), h, detail, PROBLEMS, TODAY)
    assert [r["id"] for r in rows] == ["m1"]
    assert broken == [("bob", "m2", "boom")]


def test_build_rows_member_not_in_latest_record_is_broken():
    # In config but today's record lacks them and nothing failed loudly:
    # that is the "just added, Action has not run since" case.
    h = make_history({TODAY: {"m2": member_record(1, sol=sol_all(1))}})
    rows, broken = board.build_rows(dcfg(), h, detail_for({}), PROBLEMS, TODAY)
    assert [r["id"] for r in rows] == ["m2"]
    assert broken and broken[0][1] == "m1"
    assert broken[0][2] == theme.ERR_NOT_FETCHED


def test_build_rows_stale_flag():
    h = make_history({TODAY: {"m1": member_record(1, sol=sol_all(1))}})
    detail = detail_for({}, stale=["m1"])
    rows, _ = board.build_rows(dcfg(), h, detail, PROBLEMS, TODAY)
    assert rows[0]["stale"] is True


def test_previous_ranks_and_rank_move():
    h = make_history({
        day_ago(1): {"m1": member_record(2, sol=sol_all(10)), "m2": member_record(1, sol=sol_all(5))},
        TODAY: {"m1": member_record(0, sol=sol_all(10)), "m2": member_record(2, sol=sol_all(5))},
    })
    ranks = board.previous_ranks(dcfg(), h, detail_for({}), PROBLEMS, TODAY)
    assert ranks == {"m1": 1, "m2": 2}
    assert board.rank_move("m1", 2, ranks) == f" {theme.DOWN}"
    assert board.rank_move("m2", 1, ranks) == f" {theme.UP}"
    assert board.rank_move("m3", 1, ranks) == ""  # not on yesterday's board
    assert board.rank_move("m2", 2, ranks) == ""  # unchanged


def test_previous_ranks_empty_without_yesterday():
    h = make_history({TODAY: {"m1": member_record(1, sol=sol_all(1))}})
    assert board.previous_ranks(dcfg(), h, detail_for({}), PROBLEMS, TODAY) == {}


# --- render ------------------------------------------------------------------


def render_board(h, detail=None, problems=PROBLEMS, cfg=None, unreadable=()):
    return board.render(cfg or dcfg(), h, detail or detail_for({}), problems, unreadable)


def test_render_empty_history():
    out = render_board({}, problems={})
    assert theme.EMPTY_DATA in out


def test_render_status_line_all_submitted():
    h = make_history({TODAY: {"m1": member_record(1, sol=sol_all(1)),
                              "m2": member_record(1, sol=sol_all(1))}})
    out = render_board(h)
    assert "🎉" in out and "2/2" in out
    assert theme.HEAD_BOARD in out


def test_render_pending_names():
    h = make_history({TODAY: {"m1": member_record(1, sol=sol_all(1)),
                              "m2": member_record(0, sol=sol_all(1))}})
    out = render_board(h)
    assert "pending:" in out and "bob" in out


def test_render_no_data_spark_for_missing_day():
    h = make_history({TODAY: {"m1": member_record(1, sol=sol_all(1))}})
    out = render_board(h)
    assert "░" in out  # the 13 days before today are outside history


def test_render_warn_notes_on_failures_and_stale():
    h = make_history({TODAY: {"m1": member_record(1, sol=sol_all(1))}})
    detail = detail_for({}, failed={"m2": "boom"}, stale=["m1"])
    out = render_board(h, detail=detail)
    assert "⚠️" in out
    assert "could not be fetched" in out
    assert "showing earlier data" in out


def test_render_unreadable_note():
    h = make_history({TODAY: {"m1": member_record(1, sol=sol_all(1))}})
    out = render_board(h, unreadable=("history.json",))
    assert "could not be parsed" in out


def test_render_broken_fallback_when_all_fetch_failed():
    h = make_history({TODAY: {"m1": member_record(1, sol=sol_all(1))}})
    detail = detail_for({}, failed={"m1": "boom", "m2": "boom2"})
    out = render_board(h, detail=detail)
    assert theme.HEAD_BROKEN in out
    assert "boom" in out and "boom2" in out


def test_render_stamp_uses_fetched_at_not_render_time():
    h = make_history({TODAY: {"m1": member_record(1, sol=sol_all(1))}})
    out = render_board(h)
    assert "11:00" in out  # from the fixture fetched_at
    assert "Updated" in out


def test_render_stamp_rate_hidden_below_min_slots():
    # Today's first run at hour 3: only 10 eligible slots, below the minimum
    # at which the percentage would mean anything.
    run_hours = "0" * 24
    run_hours = run_hours[:3] + "1" + run_hours[4:]
    h = {TODAY: {"run_hours": run_hours, "members": {"m1": member_record(1, sol=sol_all(1))}}}
    out = render_board(h)
    assert "⏱️" not in out


def test_render_stamp_rate_shown_when_measurable():
    h = make_history({TODAY: {"m1": member_record(1, sol=sol_all(1))},
                      day_ago(1): {"m1": member_record(1, sol=sol_all(1))}})
    out = render_board(h)
    assert "⏱️" in out
    assert "%" in out


def test_render_details_section_with_problem_links():
    detail = detail_for({"m1": recent_ac({TODAY: ["twosum", "medproblem"]})})
    h = make_history({TODAY: {"m1": member_record(2, 1, 1, 0, sol=sol_all(10))}})
    out = render_board(h, detail=detail)
    assert theme.HEAD_DETAIL in out
    assert 'leetcode.com/problems/twosum/' in out
    assert "<code>Easy</code>" in out


def test_render_detail_truncates_at_problem_limit():
    slugs = {TODAY: [f"p{i}" for i in range(25)]}
    detail = detail_for({"m1": recent_ac(slugs)})
    h = make_history({TODAY: {"m1": member_record(25, sol=sol_all(25))}})
    problems = {f"p{i}": {"difficulty": "Easy", "frontend_id": str(i), "tags": []}
                for i in range(25)}
    out = render_board(h, detail=detail, problems=problems)
    # 20 problem lines, each with a leetcode.com link, plus a trailing "…".
    assert out.count("leetcode.com/problems/p") == theme.PROBLEM_LIMIT
    assert theme.PROBLEM_MORE in out


def test_render_tags_section():
    h = make_history({TODAY: {"m1": member_record(1, sol=sol_all(1))},
                      day_ago(1): {"m1": member_record(1, sol=sol_all(1))}})
    h[TODAY]["tags"] = {"Array": 2, "Graph": 1}
    h[day_ago(1)]["tags"] = {"Array": 1}
    out = render_board(h)
    assert theme.HEAD_TAGS.format(week=7) in out
    assert "Array丨3" in out
    assert "Graph" in out  # count 1 -> bare chip, no "丨1"


def test_render_no_tags_section_when_empty():
    h = make_history({TODAY: {"m1": member_record(1, sol=sol_all(1))}})
    out = render_board(h)
    assert theme.HEAD_TAGS not in out


def test_render_medal_icons_for_first_three():
    members = [{"id": f"m{i}", "name": f"n{i}"} for i in range(1, 4)]
    h = make_history({TODAY: {m["id"]: member_record(1, sol=sol_all(1)) for m in members}})
    out = render_board(h, cfg=dcfg(members=members))
    assert "🥇" in out and "🥈" in out and "🥉" in out


def test_render_escapes_member_name():
    h = make_history({TODAY: {"m1": member_record(1, sol=sol_all(1))}})
    cfg = dcfg(members=[{"id": "m1", "name": '<script>alert(1)</script>'}])
    out = render_board(h, cfg=cfg)
    assert "<script>" not in out
    assert "&lt;script&gt;" in out


# --- update_readme -----------------------------------------------------------


def test_update_readme_roundtrip(paths, fixed_now, monkeypatch):
    import common as C

    C.README.write_text(
        f"# Board\n\n{C.MARK_START}\n\nold board\n\n{C.MARK_END}\n\nfooter\n",
        encoding="utf-8",
    )
    h = make_history({TODAY: {"m1": member_record(2, 1, 1, 0, sol=sol_all(10))}})
    C.save_history({"timezone": "UTC", "score_weights": {}, "fetched_at": "x", "days": h})
    C.save_today(detail_for({}))
    C.save_problems(PROBLEMS)
    monkeypatch.setattr(board, "README", C.README)

    eod = board.update_readme(dcfg())

    text = C.README.read_text(encoding="utf-8")
    assert "alice" in text and "old board" not in text
    assert text.endswith("footer\n")
    assert eod["m1"] == 1  # streak began today, so eod is 1


def test_update_readme_missing_markers_raises(paths, fixed_now, monkeypatch):
    import common as C

    C.README.write_text("no markers here", encoding="utf-8")
    monkeypatch.setattr(board, "README", C.README)
    with pytest.raises(SystemExit, match="markers"):
        board.update_readme(dcfg())