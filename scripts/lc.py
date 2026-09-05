"""LeetCode public GraphQL client. Read-only public data, no login required."""

import json
import ssl
import time
import urllib.error
import urllib.request

ENDPOINT = "https://leetcode.com/graphql"
UA = "Mozilla/5.0 (LeetTogether; +https://github.com)"


def _ssl_context():
    """Default trust store, falling back to certifi if the interpreter has none.

    python.org's macOS builds bundle their own OpenSSL, ignore the system keychain,
    and start with an empty trust store until Install Certificates.command is run.
    certifi ships with that same installer, so preferring it keeps this working
    without asking anyone to repair their Python first.
    """
    ctx = ssl.create_default_context()
    if ctx.cert_store_stats()["x509_ca"]:
        return ctx
    try:
        import certifi
    except ImportError:
        return ctx  # nothing better available; the TLS error will say so
    ctx.load_verify_locations(certifi.where())
    return ctx


SSL_CONTEXT = _ssl_context()

# One request covers it all: solved counts and the recent accepted list.
#
# Asks for nothing it does not use, with one deliberate exception: `userCalendar`
# is requested and discarded, because asking for it is what makes an official or
# special account fail loudly instead of silently returning nothing. `profile` is
# left out entirely — it carries realName, and a public board should not even
# receive a field it has no business publishing.
USER_QUERY = """
query userProgress($handle: String!) {
  matchedUser(username: $handle) {
    username
    submitStats { acSubmissionNum { difficulty count } }
    userCalendar { streak }
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
    questionFrontendId
    title
    difficulty
    topicTags { name }
  }
}
"""

# recentAcSubmissionList cap. Hitting it means older records were truncated.
RECENT_LIMIT = 20

# Only these HTTP codes are worth a second try; the rest are permanent.
RETRY_CODES = {429, 500, 502, 503, 504}


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
            with urllib.request.urlopen(req, timeout=20, context=SSL_CONTEXT) as resp:
                return json.loads(resp.read())
        # HTTPError subclasses URLError, so it has to be caught first
        except urllib.error.HTTPError as exc:
            last = exc
            if exc.code not in RETRY_CODES:
                break
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
            last = exc
        if attempt < retries - 1:  # no point sleeping after the final attempt
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
    return {
        "ok": True,
        "handle": user["username"],
        "solved": {
            "all": counts.get("all", 0),
            "easy": counts.get("easy", 0),
            "medium": counts.get("medium", 0),
            "hard": counts.get("hard", 0),
        },
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
        "frontend_id": q.get("questionFrontendId") or "",
        "difficulty": q.get("difficulty") or "",
        "tags": [t["name"] for t in (q.get("topicTags") or [])],
    }
