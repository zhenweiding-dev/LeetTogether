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
    score_of,
)


def sync_questions(members):
    """Fill in difficulty and tags for new problems, queried once each.

    Entries in the old cache format are re-queried to pick up their tags.
    """
    problems = load_problems()
    slugs = {
        s["slug"]
        for m in members.values()
        if m.get("ok")
        for s in m.get("recent_ac", [])
    }
    missing = sorted(s for s in slugs if not isinstance(problems.get(s), dict))
    if not missing:
        return

    print(f"\nFetching difficulty and tags for {len(missing)} new problem(s)...")
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


def fetch_members(cfg):
    members, failures = {}, []

    for i, m in enumerate(cfg["members"]):
        handle = m["handle"]
        if i:
            time.sleep(0.4)  # rate limit
        try:
            data = lc.fetch_user(handle)
        except RuntimeError as exc:
            data = {"ok": False, "error": str(exc)}

        if not data["ok"]:
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
            "score": score_of(data["solved"], cfg["score_weights"]),
            "ranking": data["ranking"],
            "lc_streak": data["lc_streak"],
            "lc_active_days": data["lc_active_days"],
            # board.py uses this to decide the coverage boundary
            "recent_truncated": len(recent) >= lc.RECENT_LIMIT,
            "recent_ac": recent,
        }
        print(f"  {handle}: {data['solved']['all']} solved, {len(recent)} recent ACs")

    return members, failures


def main():
    cfg = load_config()
    if not cfg["members"]:
        raise SystemExit("No members in config.json. Run `python3 scripts/add.py`.")

    today = local_now(cfg).strftime("%Y-%m-%d")
    members, failures = fetch_members(cfg)
    sync_questions(members)

    SNAP_DIR.mkdir(parents=True, exist_ok=True)
    out = SNAP_DIR / f"{today}.json"
    out.write_text(
        json.dumps(
            {
                "date": today,
                "timezone": cfg["timezone"],
                "fetched_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                "score_weights": cfg["score_weights"],
                "members": members,
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )

    board.update_readme(cfg)
    print(f"\nWrote snapshot {out.name}, README board updated")

    if failures:
        print(f"\n{len(failures)} member(s) failed:", file=sys.stderr)
        for handle, err in failures:
            print(f"  {handle} - {err}", file=sys.stderr)
        print("Fix the username in config.json, or re-run add.py.", file=sys.stderr)


if __name__ == "__main__":
    main()
