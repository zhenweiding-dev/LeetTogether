"""Fetch every member's progress, roll the history window, refresh the README board.

    python3 scripts/update.py

Two files, both bounded. data/history.json keeps board.RETAIN days of totals;
data/today.json holds today's problem lists and is replaced, never appended to.
"""

import sys
import time
from datetime import datetime, timedelta, timezone

import board
import lc
import theme
from common import (
    HANDLES_ENV,
    load_config,
    load_handles,
    load_history,
    load_problems,
    load_today,
    local_date,
    local_now,
    save_history,
    save_problems,
    save_today,
)


def sync_questions(members):
    """Fill in the number, difficulty and tags for new problems, once each.

    Entries cached before a field existed are re-queried to pick it up. Returns the
    cache, which the caller needs to aggregate the day.
    """
    problems = load_problems()
    slugs = {
        s["slug"]
        for m in members.values()
        if m.get("ok")
        for s in m.get("recent_ac", [])
    }
    missing = sorted(
        s
        for s in slugs
        if not isinstance(problems.get(s), dict)
        or "frontend_id" not in problems[s]
    )
    if not missing:
        return problems

    print(f"\nFetching metadata for {len(missing)} problem(s)...")
    for i, slug in enumerate(missing):
        if i:
            time.sleep(0.3)
        try:
            meta = lc.fetch_question(slug)
        except RuntimeError as exc:
            print(f"  {slug}: {exc}", file=sys.stderr)
            continue
        if meta:
            problems[slug] = meta
    save_problems(problems)
    return problems


def top_up_yesterday(history, detail, problems, cfg, today):
    """Let today's fetch raise yesterday's totals, never lower them.

    A submission made after yesterday's final run is only visible now, and the
    problem list behind it is gone tomorrow, so this is its one chance to be
    counted. Upward only: today's window may no longer reach back that far, and a
    short read must not shrink a day that was recorded correctly at the time.
    """
    prev = (
        datetime.strptime(today, "%Y-%m-%d").date() - timedelta(days=1)
    ).isoformat()
    entry = history.get(prev)
    if not entry:
        return
    seen = []
    raised = False
    for mid, m in (entry.get("members") or {}).items():
        slugs = sorted(board.day_events(mid, detail, cfg, prev))
        counts = board.day_counts(slugs, problems)
        if counts["count"] > (m.get("day") or {}).get("count", 0):
            m["day"] = counts
            raised = True
        seen += slugs
    # The group histogram is only replaced when it can be rebuilt in full.
    if raised and seen:
        entry["tags"] = board.tag_histogram(seen, problems)


def core(members):
    """The only two things whose change means the data actually moved.

    Compared rather than the whole record because the rest is either derived from
    these (the day counts), written back by the board (the streak), or the same
    every run (the name).
    """
    return {
        mid: (m.get("solved"), m.get("recent_ac"))
        for mid, m in members.items()
        if m.get("ok")
    }


def mark_run(prev, hour):
    """The day's run log with this hour set: 24 chars, one per local hour.

    GitHub silently drops scheduled runs, so the board reports a measured hit rate
    instead of a number someone wrote down once. One character per hour rather than
    a list of timestamps, so a re-run in the same hour cannot inflate it and the
    hourly diff stays a single line.
    """
    mask = list((prev or {}).get("run_hours") or "0" * 24)
    mask = (mask + ["0"] * 24)[:24]
    mask[hour] = "1"
    return "".join(mask)


def fetch_members(cfg, handles, earlier):
    """Fetch each member, keyed by their config id. Handles never leave this function."""
    members, failures, kept = {}, [], []

    for i, m in enumerate(cfg["members"]):
        mid = m["id"]
        name = m.get("name") or mid
        handle = handles.get(mid)
        if i:
            time.sleep(0.4)  # rate limit
        if not handle:
            data = {"ok": False, "error": theme.ERR_NO_HANDLE}
        else:
            try:
                data = lc.fetch_user(handle)
            except RuntimeError as exc:
                data = {"ok": False, "error": str(exc)}

        if not data["ok"]:
            # A blip must not wipe data already collected today, so reuse it.
            good = earlier.get(mid)
            if good and good.get("ok"):
                # flagged so the board can say the numbers are not fresh
                members[mid] = {**good, "stale": True}
                kept.append((mid, data["error"]))
                print(f"  {name}: {data['error']} (kept earlier)", file=sys.stderr)
                continue
            failures.append((mid, data["error"]))
            members[mid] = {
                "name": name,
                "ok": False,
                "error": data["error"],
            }
            print(f"  {name}: {data['error']}", file=sys.stderr)
            continue

        recent = data["recent_ac"]
        members[mid] = {
            # config.json only, never the profile's real name: this file is public
            # and nobody should be outed by a field they forgot was on LeetCode.
            "name": name,
            "ok": True,
            "solved": data["solved"],
            "recent_ac": recent,
        }
        print(f"  {name}: {data['solved']['all']} solved, {len(recent)} recent ACs")

    return members, failures, kept


def main():
    cfg = load_config()
    if not cfg["members"]:
        raise SystemExit("No members in config.json. Run `python3 scripts/add.py`.")
    handles = load_handles()
    if not handles:
        raise SystemExit(
            f"No LeetCode handles. Set the {HANDLES_ENV} secret, or run\n"
            "`python3 scripts/add.py` to write handles.local.json."
        )

    now = local_now(cfg)
    today = now.strftime("%Y-%m-%d")

    stored, _ = load_history()
    history = stored.get("days") or {}
    detail, _ = load_today()
    # Anything from an earlier day is a fresh start for today.json.
    if detail.get("date") != today:
        detail = {"date": today, "members": {}}
    # Rebuilt whole, because a member whose fetch fails later in this run is
    # carried forward from it verbatim.
    names = {m["id"]: m.get("name") or m["id"] for m in cfg["members"]}
    prev_members = {
        mid: {
            "name": names.get(mid, mid),
            "ok": True,
            **((history.get(today, {}).get("members") or {}).get(mid) or {}),
            **m,
        }
        for mid, m in (detail.get("members") or {}).items()
    }

    members, failures, kept = fetch_members(cfg, handles, prev_members)
    problems = sync_questions(members)

    day_slugs = {}
    for mid, m in members.items():
        if m.get("ok"):
            day_slugs[mid] = sorted(
                {s["slug"] for s in m["recent_ac"] if local_date(s["ts"], cfg) == today}
            )
            m["day"] = board.day_counts(day_slugs[mid], problems)

    # Hold on to any streak already stored; the board recomputes it below.
    for mid, m in members.items():
        if "streak" in (history.get(today, {}).get("members", {}).get(mid, {})):
            m["streak"] = history[today]["members"][mid]["streak"]

    # A run that finds nothing new keeps the old timestamp, so both files and the
    # board's "Updated" line stay byte-identical and the Action skips the commit.
    unchanged = core(prev_members) == core(members) and bool(prev_members)
    fetched_at = (
        detail.get("fetched_at")
        if unchanged and detail.get("fetched_at")
        else datetime.now(timezone.utc).isoformat(timespec="seconds")
    )

    # today.json carries the problem lists and everything about this run;
    # history.json carries numbers and nothing else.
    detail = {
        "date": today,
        "fetched_at": fetched_at,
        "members": {
            mid: {"recent_ac": m["recent_ac"]}
            for mid, m in members.items()
            if m.get("ok")
        },
        "failed": {mid: m["error"] for mid, m in members.items() if not m.get("ok")},
        "stale": sorted(mid for mid, m in members.items() if m.get("stale")),
    }
    history[today] = {
        "run_hours": mark_run(history.get(today), now.hour),
        "tags": board.tag_histogram(
            [s for slugs in day_slugs.values() for s in slugs], problems
        ),
        # Numbers only: no name (config has it), no ok/error/stale (this run's
        # business, in today.json), no lc_streak (the board never reads it).
        "members": {
            mid: {"solved": m["solved"], "day": m["day"], **({"streak": m["streak"]} if "streak" in m else {})}
            for mid, m in members.items()
            if m.get("ok")
        },
    }
    top_up_yesterday(history, detail, problems, cfg, today)

    # The window is why this project does not grow without bound.
    for date in sorted(history)[: -board.RETAIN]:
        del history[date]

    def write():
        save_history(
            {
                "timezone": cfg["timezone"],
                "score_weights": cfg["score_weights"],
                "fetched_at": fetched_at,
                "days": dict(sorted(history.items())),
            }
        )
        save_today(detail)

    write()
    # The board hands back today's end-of-day streaks so tomorrow can carry them
    # forward instead of re-deriving them.
    for mid, eod in board.update_readme(cfg).items():
        if mid in history[today]["members"]:
            history[today]["members"][mid]["streak"] = eod
    write()

    verb = "unchanged" if unchanged else "updated"
    print(f"\nData {verb} ({len(history)} day(s) kept), README board rewritten")

    if kept:
        print(
            f"\n{len(kept)} member(s) failed but kept today's earlier data:",
            file=sys.stderr,
        )
        for mid, err in kept:
            print(f"  {mid} - {err}", file=sys.stderr)

    if failures:
        print(f"\n{len(failures)} member(s) failed:", file=sys.stderr)
        for mid, err in failures:
            print(f"  {mid} - {err}", file=sys.stderr)
        print(
            "`does not exist` means the wrong username behind that id. A TLS or network\n"
            "error is local: CERTIFICATE_VERIFY_FAILED means this Python has no CA\n"
            'bundle — on macOS run "/Applications/Python 3.x/Install Certificates.command".',
            file=sys.stderr,
        )


if __name__ == "__main__":
    main()
