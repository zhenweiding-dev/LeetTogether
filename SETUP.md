# Set up your own

↩ [Back to the board](README.md)

LeetTogether keeps a small group's LeetCode progress in a single README. No server,
no database, no login, no API key — a GitHub Action reads everyone's public profile
every hour and rewrites the table on the front page.

## Quick start

1. [Use this template](https://github.com/zhenweiding-dev/LeetTogether/generate) to
   create your own repo

2. Clear this group's data — GitHub copies a template verbatim, so it comes along:

   ```bash
   python3 scripts/clear.py
   ```

   Then set `timezone` in `config.json` to your
   [IANA name](https://en.wikipedia.org/wiki/List_of_tz_database_time_zones).

3. Add everyone. This only writes `config.json`:

   ```bash
   python3 scripts/add.py
   ```

4. `git push` — the hourly Action builds the board from there

That's the whole setup. Python standard library only, nothing to install. The
Action takes over from there per hour.

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

Ranking is **today's points**, so it resets every morning and nobody is ever out of
reach — lifetime totals never enter into it. Ties fall back to this week's points,
then the streak. Points are difficulty-weighted (Easy 1 / Medium 3 / Hard 6) so
grinding Easies doesn't move you up. Solving the same problem twice in one day
counts once; coming back to it another day counts again, because revisiting is
practice.

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
| `scripts/clear.py` | wipe the inherited data before the first run |
| `scripts/add.py` | add members to `config.json`, nothing else |
| `scripts/update.py` | fetch, snapshot, rewrite the board |
| `scripts/theme.py` | every label, emoji and tag icon the board renders |
| `scripts/board.py` | metrics and rendering |
| `scripts/lc.py` | GraphQL client |
| `scripts/common.py` | paths, config and cache I/O |

## Notes

- Under **Settings → Actions → General**, new repos default the token to read-only.
  The workflow already asks for `contents: write` — leave that block in place or the
  daily commit fails with a 403.
- The Action runs hourly, so the daily ranking moves through the day. GitHub's cron
  can be delayed by up to an hour at peak, and skips runs when the queue is busy.
- Scheduled workflows are disabled after 60 days of repository inactivity. GitHub
  emails first, and one manual run brings it back.
- Works with `leetcode.com`. `leetcode.cn` is a separate account system with a
  different GraphQL schema — not supported yet.
