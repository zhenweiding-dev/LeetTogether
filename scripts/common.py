"""Shared config and small helpers."""

import json
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parent.parent
CONFIG_PATH = ROOT / "config.json"
DATA_DIR = ROOT / "data"
SNAP_DIR = DATA_DIR / "snapshots"
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


def tags_of(problems, slug):
    v = problems.get(slug)
    return v.get("tags") or [] if isinstance(v, dict) else []


def save_problems(problems):
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    PROBLEMS_PATH.write_text(
        json.dumps(problems, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def load_snapshots():
    """[(date, snapshot)] in ascending date order."""
    if not SNAP_DIR.exists():
        return []
    out = []
    for path in sorted(SNAP_DIR.glob("*.json")):
        try:
            out.append((path.stem, json.loads(path.read_text(encoding="utf-8"))))
        except json.JSONDecodeError:
            continue
    return out


def days_back(end_str, n):
    """n dates ending at end_str, ascending."""
    end = datetime.strptime(end_str, "%Y-%m-%d").date()
    return [(end - timedelta(days=i)).isoformat() for i in range(n - 1, -1, -1)]
