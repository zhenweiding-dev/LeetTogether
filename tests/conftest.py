"""Shared fixtures for the offline suite.

Everything here is synthetic: no network, no LeetCode, no handles file in the
repo. The scripts only touch disk through paths in `common`, and only ever call
LeetCode through `lc`, so both are patched per-test to point at tmp_path and a
fake fetcher respectively.
"""

import json
from datetime import datetime, timedelta, timezone

import pytest

import common

# A fixed "today" for every test, so streak/window math is deterministic.
TODAY = "2026-09-25"
NOW = datetime(2026, 9, 25, 12, 0, tzinfo=timezone.utc)

CFG = {
    "timezone": "UTC",
    "score_weights": {"easy": 1, "medium": 3, "hard": 6},
    "members": [
        {"id": "m1", "name": "alice"},
        {"id": "m2", "name": "bob"},
    ],
}

PROBLEMS = {
    "twosum": {"difficulty": "Easy", "frontend_id": "1", "tags": ["Array", "Hash Table"]},
    "medproblem": {"difficulty": "Medium", "frontend_id": "2", "tags": ["Dynamic Programming"]},
    "hardproblem": {"difficulty": "Hard", "frontend_id": "3", "tags": ["Graph"]},
}

# Probing /tz fixtures --------------------------------------------------------


def ts(day, hour=10):
    """Unix seconds for a UTC datetime on the given %Y-%m-%d."""
    dt = datetime.strptime(day, "%Y-%m-%d").replace(hour=hour, tzinfo=timezone.utc)
    return int(dt.timestamp())


def solved(all_, easy, medium, hard):
    return {"all": all_, "easy": easy, "medium": medium, "hard": hard}


def sol_all(n):
    return solved(n, n, 0, 0)


def member_record(count, easy=0, medium=0, hard=0, sol=None, streak=None):
    m = {"day": {"count": count, "easy": easy, "medium": medium, "hard": hard}}
    if sol is not None:
        m["solved"] = sol
    if streak is not None:
        m["streak"] = streak
    return m


def history_entry(members, tags=None, run_hours="1" * 24):
    e = {"run_hours": run_hours, "members": members}
    if tags is not None:
        e["tags"] = tags
    return e


def make_history(days_cfg):
    """days_cfg: {date: {mid: member_record}}. No tags unless a test adds them."""
    return {date: history_entry(members) for date, members in days_cfg.items()}


def day_ago(n, today=TODAY):
    d = datetime.strptime(today, "%Y-%m-%d").date() - timedelta(days=n)
    return d.isoformat()


def recent_ac(slugs_by_day):
    """[{slug, title, ts}] from {date: [slug]} — most recent first, like the API."""
    items = [
        {"slug": slug, "title": slug, "ts": ts(date)}
        for date, slugs in slugs_by_day.items()
        for slug in slugs
    ]
    return sorted(items, key=lambda s: -s["ts"])


def detail_for(members_recent, today=TODAY, failed=None, stale=None):
    return {
        "date": today,
        "fetched_at": f"{today}T11:00:00+00:00",
        "members": {mid: {"recent_ac": ac} for mid, ac in members_recent.items()},
        "failed": failed or {},
        "stale": stale or [],
    }


# Path redirection ------------------------------------------------------------


@pytest.fixture
def paths(tmp_path, monkeypatch):
    """Point every data-file path common knows about at tmp_path."""
    for name in (
        "CONFIG_PATH",
        "HANDLES_PATH",
        "HISTORY_PATH",
        "TODAY_PATH",
        "PROBLEMS_PATH",
        "README",
    ):
        monkeypatch.setattr(common, name, tmp_path / f"{name.lower()}.json")
    monkeypatch.setattr(common, "DATA_DIR", tmp_path)
    return tmp_path


@pytest.fixture
def fixed_now(monkeypatch):
    import board
    import update

    monkeypatch.setattr(board, "local_now", lambda cfg: NOW)
    monkeypatch.setattr(update, "local_now", lambda cfg: NOW)
    return NOW


@pytest.fixture
def fake_lc(monkeypatch):
    """lc.fetch_user / lc.fetch_question driven by a scriptable dict."""

    import lc

    class FakeLC:
        def __init__(self):
            self.users = {}
            self.questions = {}
            self.user_calls = []
            self.question_calls = []

        def fetch_user(self, handle):
            self.user_calls.append(handle)
            if handle in self.users:
                return self.users[handle]
            return {"ok": False, "error": "That user does not exist."}

        def fetch_question(self, slug):
            self.question_calls.append(slug)
            return self.questions.get(slug)

    fake = FakeLC()
    monkeypatch.setattr(lc, "fetch_user", fake.fetch_user)
    monkeypatch.setattr(lc, "fetch_question", fake.fetch_question)
    return fake


def write_json(path, data):
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return path