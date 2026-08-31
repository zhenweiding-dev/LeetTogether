# Set up your own

↩ [Back to the board](README.md)

One README, no server, no database, no login, no API key. A GitHub Action reads
everyone's public LeetCode profile hourly and rewrites the table on the front page.

## Quick start

1. [Use this template](https://github.com/zhenweiding-dev/LeetTogether/generate)

2. Wipe this group's data — a template is copied verbatim, so it comes along. Then
   set `timezone` in `config.json` to your
   [IANA name](https://en.wikipedia.org/wiki/List_of_tz_database_time_zones).

   ```bash
   python3 scripts/clear.py
   ```

3. Add everyone. Takes a username or a profile URL, verifies it, and only writes
   `config.json` — so it can never collide with the Action.

   ```bash
   python3 scripts/add.py
   ```

4. `git push`

Python standard library only, nothing to install. Nothing for the others to do
either: a normal LeetCode account is readable as is.

## Reading the board

| Mark | Means |
|---|---|
| `🔺` `🔻` | moved up or down since yesterday |
| `≥21` | at least 21 — the window reaches days we have no data for |
| `12+` | streak is at least 12; the snapshots cannot prove how far back it goes |
| `·` `░` | that day had no submission / is unknown |
| `⚠️` above the table | a fetch went wrong; absent when all is well |
| `😴 ✨ 💫 ⭐ 🌟 🌙 🌒 🌓 🌔 🌕 ☀️ 🌈 🦄 👑` | streak ladder, front-loaded so it moves in the first week |

Ranking is **today's points** — it resets every morning and lifetime totals never
count, so nobody is ever out of reach. Ties go to the last 7 days, then the streak.
Weights are Easy 1 / Medium 3 / Hard 6, so grinding Easies does not move you up.

Both windows are rolling, not calendar: `Last 7 days` is today plus the six before
it, and does not reset on Mondays. A problem solved twice in one day counts once;
picked up again another day it counts again.

## When a fetch fails

| Error | Cause |
|---|---|
| `That user does not exist.` | wrong username |
| `no permission to check the calendar.` | official or special account, rare |
| `request failed: ...` | network, timeout or TLS — retried, then reported |

Nothing already recorded is ever lost. If someone has good numbers from earlier
today the board keeps them and says so at the top; only a member with no data at all
drops out of the table.

## Files

| Path | Purpose |
|---|---|
| `config.json` | members, timezone, scoring weights |
| `data/snapshots/<date>.json` | one per day; left untouched when a run finds nothing new |
| `data/problems.json` | slug → number, difficulty, tags — queried once per problem |
| `scripts/theme.py` | every label, emoji and threshold the board renders |
| `scripts/board.py` | metrics and rendering |
| `scripts/update.py` | fetch, snapshot, rewrite the board — what the Action runs |

## Notes

- Under **Settings → Actions → General**, new repos default the token to read-only.
  The workflow asks for `contents: write` — leave that block in or the commit 403s.
- The cron fires at `:37`, not on the hour, because that is when GitHub's scheduled
  queue is least loaded. Runs still get dropped: this repo hit 59% over 87 hours,
  with occasional 10-hour gaps. Harmless unless someone solves more than 20 problems
  inside a single gap.
- Scheduled workflows stop after 60 days of repository inactivity; GitHub emails
  first and one manual run brings them back.
- `leetcode.com` only. `leetcode.cn` is a separate account system with a different
  GraphQL schema.
