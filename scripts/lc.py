"""LeetCode public GraphQL client. Read-only public data, no login required."""

import json
import time
import urllib.error
import urllib.request

ENDPOINT = "https://leetcode.com/graphql"
UA = "Mozilla/5.0 (LeetcodeTogether; +https://github.com)"

# One request covers it all: solved counts, calendar, recent accepted list.
USER_QUERY = """
query userProgress($handle: String!) {
  matchedUser(username: $handle) {
    username
    profile { realName userAvatar ranking }
    submitStats { acSubmissionNum { difficulty count } }
    userCalendar { streak totalActiveDays submissionCalendar }
  }
  recentAcSubmissionList(username: $handle, limit: 20) {
    title
    titleSlug
    timestamp
  }
}
"""

QUESTION_QUERY = """
query questionMeta($slug: String!) {
  question(titleSlug: $slug) {
    title
    difficulty
    topicTags { name }
  }
}
"""

# recentAcSubmissionList cap. Hitting it means older records were truncated.
RECENT_LIMIT = 20


def query(gql, variables, retries=3):
    body = json.dumps({"query": gql, "variables": variables}).encode()
    req = urllib.request.Request(
        ENDPOINT,
        data=body,
        headers={"Content-Type": "application/json", "User-Agent": UA},
    )
    last = None
    for attempt in range(retries):
        try:
            with urllib.request.urlopen(req, timeout=20) as resp:
                return json.loads(resp.read())
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
            last = exc
            time.sleep(1.5 * (attempt + 1))
    raise RuntimeError(f"request failed: {last}")


def fetch_user(handle):
    """Returns {ok, ...}; on failure ok=False with a reason."""
    raw = query(USER_QUERY, {"handle": handle})
    data = raw.get("data") or {}
    user = data.get("matchedUser")

    if user is None:
        # "That user does not exist." -> bad username
        # "no permission to check the calendar." -> official/special account, rare;
        # note it nulls out all of matchedUser, not just the userCalendar field
        errs = "; ".join(e.get("message", "?") for e in raw.get("errors", []))
        return {"ok": False, "error": errs or "unknown error"}

    counts = {
        row["difficulty"].lower(): row["count"]
        for row in user["submitStats"]["acSubmissionNum"]
    }
    cal = user.get("userCalendar") or {}

    return {
        "ok": True,
        "handle": user["username"],
        "real_name": (user.get("profile") or {}).get("realName") or "",
        "ranking": (user.get("profile") or {}).get("ranking"),
        "solved": {
            "all": counts.get("all", 0),
            "easy": counts.get("easy", 0),
            "medium": counts.get("medium", 0),
            "hard": counts.get("hard", 0),
        },
        # Official streak is bucketed by UTC day; the board ignores it, kept for reference
        "lc_streak": cal.get("streak", 0),
        "lc_active_days": cal.get("totalActiveDays", 0),
        "recent_ac": [
            {"title": s["title"], "slug": s["titleSlug"], "ts": int(s["timestamp"])}
            for s in (data.get("recentAcSubmissionList") or [])
        ],
    }


def fetch_question(slug):
    """Problem difficulty and topic tags."""
    q = (query(QUESTION_QUERY, {"slug": slug}).get("data") or {}).get("question")
    if not q:
        return None
    return {
        "difficulty": q.get("difficulty") or "",
        "tags": [t["name"] for t in (q.get("topicTags") or [])],
    }
