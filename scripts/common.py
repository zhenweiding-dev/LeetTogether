"""Shared config and small helpers."""

import json
import os
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parent.parent
CONFIG_PATH = ROOT / "config.json"
HANDLES_PATH = ROOT / "handles.local.json"
HANDLES_ENV = "LC_HANDLES"
DATA_DIR = ROOT / "data"
# Two files, both bounded. history.json is a rolling window of daily totals;
# today.json is the only place a problem list ever lives, and it is replaced every
# day rather than accumulated.
HISTORY_PATH = DATA_DIR / "history.json"
TODAY_PATH = DATA_DIR / "today.json"
PROBLEMS_PATH = DATA_DIR / "problems.json"
README = ROOT / "README.md"

MARK_START = "<!-- LEADERBOARD:START -->"
MARK_END = "<!-- LEADERBOARD:END -->"


def load_config():
    cfg = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    cfg.setdefault("timezone", "UTC")
    cfg.setdefault("score_weights", {"easy": 1, "medium": 3, "hard": 6})
    return cfg


def save_config(cfg):
    CONFIG_PATH.write_text(
        json.dumps(cfg, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )


def load_handles():
    """{member id: LeetCode handle}.

    Deliberately not in config.json: the repo is meant to be shareable without
    carrying the mapping from a codename back to a real account. The Action reads
    it from the LC_HANDLES secret, a local run from a file git ignores. Nothing
    else in the project ever sees a handle.
    """
    raw = os.environ.get(HANDLES_ENV)
    if raw and raw.strip():
        return json.loads(raw)
    if HANDLES_PATH.exists():
        return json.loads(HANDLES_PATH.read_text(encoding="utf-8"))
    return {}


def save_handles(handles):
    HANDLES_PATH.write_text(
        json.dumps(handles, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def tz_of(cfg):
    return ZoneInfo(cfg["timezone"])


def local_now(cfg):
    return datetime.now(tz_of(cfg))


def local_date(ts, cfg):
    """Unix seconds -> local date string."""
    return datetime.fromtimestamp(ts, tz_of(cfg)).strftime("%Y-%m-%d")


def load_problems():
    """slug -> {difficulty, tags}."""
    if PROBLEMS_PATH.exists():
        return json.loads(PROBLEMS_PATH.read_text(encoding="utf-8"))
    return {}


def difficulty_of(problems, slug):
    v = problems.get(slug)  # older caches stored the difficulty string directly
    return (v.get("difficulty") if isinstance(v, dict) else v) or ""


def frontend_id_of(problems, slug):
    """The number LeetCode shows for the problem, or "" for an older cache entry."""
    v = problems.get(slug)
    return (v.get("frontend_id") or "") if isinstance(v, dict) else ""


def tags_of(problems, slug):
    v = problems.get(slug)
    return v.get("tags") or [] if isinstance(v, dict) else []


def save_problems(problems):
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    PROBLEMS_PATH.write_text(
        json.dumps(problems, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def _read(path, empty):
    """Parse a data file, treating a broken one as missing rather than fatal.

    Returns (contents, unreadable name or None) so the caller can put the failure
    on the board instead of silently losing a window of history to it.
    """
    if not path.exists():
        return empty, None
    try:
        return json.loads(path.read_text(encoding="utf-8")), None
    except (json.JSONDecodeError, OSError):
        return empty, path.name


def load_history():
    """The rolling window: ({date: {run_hours, members}}, unreadable name or None)."""
    data, bad = _read(HISTORY_PATH, {})
    return data, bad


def save_history(history):
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    HISTORY_PATH.write_text(
        json.dumps(history, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )


def load_today():
    """Today's problem lists: ({date, fetched_at, members}, unreadable name or None)."""
    data, bad = _read(TODAY_PATH, {})
    return data, bad


def save_today(today):
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    TODAY_PATH.write_text(
        json.dumps(today, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )


def days_back(end_str, n):
    """n dates ending at end_str, ascending."""
    end = datetime.strptime(end_str, "%Y-%m-%d").date()
    return [(end - timedelta(days=i)).isoformat() for i in range(n - 1, -1, -1)]
