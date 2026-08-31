"""Fetch every member's progress, write today's snapshot, refresh the README board.

    python3 scripts/update.py

A snapshot holds cumulative solved counts plus the 20 most recent ACs at that
moment; board.py derives every metric from those snapshots.
"""

import json
import sys
import time
from datetime import datetime, timezone

import board
import lc
from common import (
    SNAP_DIR,
    load_config,
    load_problems,
    local_now,
    save_problems,
)


def sync_questions(members):
    """Fill in the number, difficulty and tags for new problems, once each.

    Entries cached before a field existed are re-queried to pick it up.
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
        return

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


def load_today(path):
    """Today's snapshot, if this is not the first run of the day."""
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return None


def core(members):
    """Members minus fields the board writes back, for change detection."""
    return {h: {k: v for k, v in m.items() if k != "streak"} for h, m in members.items()}


def fetch_members(cfg, earlier):
    members, failures, kept = {}, [], []

    for i, m in enumerate(cfg["members"]):
        handle = m["handle"]
        if i:
            time.sleep(0.4)  # rate limit
        try:
            data = lc.fetch_user(handle)
        except RuntimeError as exc:
            data = {"ok": False, "error": str(exc)}

        if not data["ok"]:
            # A blip must not wipe data already collected today, so reuse it.
            good = earlier.get(handle)
            if good and good.get("ok"):
                # flagged so the board can say the numbers are not fresh
                members[handle] = {**good, "stale": True}
                kept.append((handle, data["error"]))
                print(f"  {handle}: {data['error']} (kept earlier)", file=sys.stderr)
                continue
            failures.append((handle, data["error"]))
            members[handle] = {
                "name": m.get("name") or handle,
                "ok": False,
                "error": data["error"],
            }
            print(f"  {handle}: {data['error']}", file=sys.stderr)
            continue

        recent = data["recent_ac"]
        members[handle] = {
            "name": m.get("name") or data["real_name"] or handle,
            "ok": True,
            "solved": data["solved"],
            # Kept for reference; `ranking` and `lc_active_days` are deliberately
            # not stored — they move every hour because of everyone else on
            # LeetCode, which would mean a commit every run and no real news.
            "lc_streak": data["lc_streak"],
            # board.py uses this to decide the coverage boundary
            "recent_truncated": len(recent) >= lc.RECENT_LIMIT,
            "recent_ac": recent,
        }
        print(f"  {handle}: {data['solved']['all']} solved, {len(recent)} recent ACs")

    return members, failures, kept


def main():
    cfg = load_config()
    if not cfg["members"]:
        raise SystemExit("No members in config.json. Run `python3 scripts/add.py`.")

    today = local_now(cfg).strftime("%Y-%m-%d")
    SNAP_DIR.mkdir(parents=True, exist_ok=True)
    out = SNAP_DIR / f"{today}.json"
    prev = load_today(out)
    prev_members = (prev or {}).get("members") or {}

    members, failures, kept = fetch_members(cfg, prev_members)
    sync_questions(members)

    # Hold on to any streak already stored; the board recomputes it below.
    for handle, m in members.items():
        if "streak" in prev_members.get(handle, {}):
            m["streak"] = prev_members[handle]["streak"]

    # A run that finds nothing new keeps the old timestamp, so the file and the
    # board's "Updated" line stay byte-identical and the Action skips the commit.
    unchanged = prev is not None and core(prev_members) == core(members)
    fetched_at = (
        prev["fetched_at"]
        if unchanged
        else datetime.now(timezone.utc).isoformat(timespec="seconds")
    )

    def write():
        out.write_text(
            json.dumps(
                {
                    "date": today,
                    "timezone": cfg["timezone"],
                    "fetched_at": fetched_at,
                    "score_weights": cfg["score_weights"],
                    "members": members,
                },
                ensure_ascii=False,
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )

    write()
    # The board hands back today's end-of-day streaks so tomorrow can carry them
    # forward instead of re-deriving from the 20-item windows, which slide away.
    for handle, eod in board.update_readme(cfg).items():
        if handle in members:
            members[handle]["streak"] = eod
    write()

    verb = "unchanged" if unchanged else "updated"
    print(f"\nSnapshot {out.name} {verb}, README board rewritten")

    if kept:
        print(
            f"\n{len(kept)} member(s) failed but kept today's earlier data:",
            file=sys.stderr,
        )
        for handle, err in kept:
            print(f"  {handle} - {err}", file=sys.stderr)

    if failures:
        print(f"\n{len(failures)} member(s) failed:", file=sys.stderr)
        for handle, err in failures:
            print(f"  {handle} - {err}", file=sys.stderr)
        print(
            "`does not exist` means a wrong username in config.json. A TLS or network\n"
            "error is local: CERTIFICATE_VERIFY_FAILED means this Python has no CA\n"
            'bundle — on macOS run "/Applications/Python 3.x/Install Certificates.command".',
            file=sys.stderr,
        )


if __name__ == "__main__":
    main()
