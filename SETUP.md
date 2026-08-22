# Set up your own

↩ [Back to the board](README.md)

LeetTogether keeps a small group's LeetCode progress in a single README. No server,
no database, no login, no API key — a GitHub Action reads everyone's public profile
twice a day and rewrites the table on the front page.

## Quick start

1. [Use this template](https://github.com/zhenweiding-dev/LeetTogether/generate) to
   create your own copy
2. Add everyone — it refreshes the board before exiting:

   ```bash
   python3 scripts/add.py
   ```

3. `git push`

That's the whole setup. Python standard library only, nothing to install. The
Action takes over from there, twice a day.

## Adding members

`add.py` takes a username or a profile URL and verifies it before saving:

```
Username or profile URL (blank to finish): leetcode.com/u/alice/
  checking alice...
  ok - 226 solved (E 64 / M 140 / H 22), 20 recent ACs
  display name [Alice]: alice
  written to config.json
```

Accepted forms: `https://leetcode.com/u/alice/`, `leetcode.com/alice`,
`leetcode.com/profile/alice/`, `alice`. Add several in a row; blank input finishes.
You can also pass one in directly:

```bash
python3 scripts/add.py leetcode.com/u/alice/
```

Nothing to install on their side and no privacy settings to change. What can fail:

| Error | Cause |
|---|---|
| `That user does not exist.` | wrong username |
| `no permission to check the calendar.` | official or special account, rare |
| `request failed: ...` | network, timeout or TLS — retried, then reported |

To refresh without adding anyone:

```bash
python3 scripts/update.py
```

A failed fetch never destroys data. If someone already has good numbers from
earlier today, the board keeps them and says so at the top; only a member with no
data at all drops out of the table.

## Reading the board

The board carries its own legend in the footer under the table — `🔺🔻` rank moves,
`+` and `≥` for lower bounds, `·` for a day with no submission and `░` for a day
we have no data on. Two things the legend does not spell out:

- A `⚠️` line above the table means a fetch went wrong. It is absent when
  everything is fine.
- `📅 Today's submissions` is ordered by today's volume, so it does not follow the
  leaderboard.

Ranking is **this week's points**, not lifetime totals, so someone in their second
week can beat someone with 900 problems solved. Points are difficulty-weighted
(Easy 1 / Medium 3 / Hard 6) so grinding Easies doesn't move you up. Solving the
same problem twice in one day counts once; coming back to it another day counts
again, because revisiting is practice.

## How it works

LeetCode serves public profile data over an unauthenticated GraphQL endpoint. Three
fields cover the whole board:

| Field | Gives us |
|---|---|
| `submitStats.acSubmissionNum` | lifetime solved counts by difficulty |
| `recentAcSubmissionList` | last 20 accepted problems, second-precision timestamps |
| `question(titleSlug:).topicTags` | difficulty and topics, looked up once per problem |

Every number comes from those timestamps bucketed into days in the configured
timezone, not from diffing yesterday's totals — so the board is complete on day one
instead of after a week. Streaks are computed the same way rather than read from
LeetCode's `userCalendar`, which buckets by UTC day and therefore rolls over at 5pm
in California.

The 20-item cap is the one real constraint. Each daily snapshot keeps its own
20-item window and the board takes the union across all of them, so the reachable
history grows the longer it runs. Anything outside that union is reported as unknown
rather than as zero — a fetch we missed should never look like a day somebody
skipped.

## Configuration

```json
{
  "timezone": "America/Los_Angeles",
  "score_weights": { "easy": 1, "medium": 3, "hard": 6 },
  "members": [
    { "handle": "alice", "name": "alice" }
  ]
}
```

| Path | Purpose |
|---|---|
| `config.json` | members, timezone, scoring weights |
| `data/snapshots/<date>.json` | one snapshot per day; re-running the same day overwrites |
| `data/problems.json` | slug → difficulty and tags, cached forever |
| `scripts/add.py` | add members, then refresh |
| `scripts/update.py` | fetch, snapshot, rewrite the board |
| `scripts/theme.py` | every label, emoji and tag icon the board renders |
| `scripts/board.py` | metrics and rendering |
| `scripts/lc.py` | GraphQL client |
| `scripts/common.py` | paths, config and cache I/O |

## Notes

- Under **Settings → Actions → General**, new repos default the token to read-only.
  The workflow already asks for `contents: write` — leave that block in place or the
  daily commit fails with a 403.
- The Action runs at ~12:00 and ~23:50 local time. GitHub's cron is UTC and can be
  delayed by up to an hour at peak.
- Scheduled workflows are disabled after 60 days of repository inactivity. GitHub
  emails first, and one manual run brings it back.
- Works with `leetcode.com`. `leetcode.cn` is a separate account system with a
  different GraphQL schema — not supported yet.
