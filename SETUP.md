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

3. Add everyone. Takes a username or a profile URL, verifies it, and asks for the
   codename to show on the board.

   ```bash
   python3 scripts/add.py
   ```

   It writes two files: `config.json`, which holds only codenames and opaque ids
   (`m1`, `m2`, …) and is safe to commit, and `handles.local.json`, which holds the
   real LeetCode handles and is git-ignored.

4. Give the Action its own copy of the handles — it cannot read the ignored file.

   ```bash
   gh secret set LC_HANDLES < handles.local.json
   ```

5. `git push`

Python standard library only, nothing to install. Nothing for the others to do
either: a normal LeetCode account is readable as is.

## Reading the board

| Mark | Means |
|---|---|
| `🔺` `🔻` | moved up or down since yesterday |
| `≥21` | at least 21 — the window reaches back past the oldest day held |
| `12+` | streak is at least 12; the history does not reach far enough to prove more |
| `·` `░` | that day had no submission / is unknown |
| `⚠️` above the table | a fetch went wrong; absent when all is well |
| `😴 ✨ 💫 ⭐ 🌟 🌙 🌒 🌓 🌔 🌕 ☀️ 🌈 🦄 👑` | streak ladder, front-loaded so it moves in the first week |

Only 20 recent solves come back per fetch, so a 20-problem day used to read `≥20`.
It no longer does: the lifetime totals on consecutive days say exactly how many
problems were new that day, and the board uses that whenever the fetch window
truncated. `≥` is left for the one thing nothing can recover — days from before the
group started tracking, or older than the window keeps.

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
| `config.json` | codenames and ids, timezone, scoring weights — committed |
| `handles.local.json` | id → LeetCode handle — **git-ignored, never commit it** |
| `data/history.json` | 16 days of numbers, keyed by id — bounded, never grows |
| `data/today.json` | today's problem lists and this run's state — the only detail kept |
| `data/problems.json` | slug → number, difficulty, tags — queried once per problem |
| `scripts/theme.py` | every label, emoji and threshold the board renders |
| `scripts/board.py` | metrics and rendering |
| `scripts/update.py` | fetch, roll the window, rewrite the board — what the Action runs |

## Notes

- Under **Settings → Actions → General**, new repos default the token to read-only.
  The workflow asks for `contents: write` — leave that block in or the commit 403s.
- The cron fires at `:37`, not on the hour, because that is when GitHub's scheduled
  queue is least loaded. Runs still get dropped anyway, sometimes for hours. Every
  run marks its own hour in the day's record, and the board prints the measured
  hit rate in its footer, so the number is current rather than something written
  down once. A gap only costs data if someone solved more than 20 problems inside
  it, and even then the lifetime totals recover the count.
- The Action makes **one commit per day**, amended in place by each later run, so
  the history stays readable. It force-pushes that commit, which is safe because
  nothing else writes to the branch — but branch protection on `main` will block
  it, and a human commit landing mid-day correctly starts a fresh one.
- Scheduled workflows stop after 60 days of repository inactivity; GitHub emails
  first and one manual run brings them back.
- `leetcode.com` only. `leetcode.cn` is a separate account system with a different
  GraphQL schema.

## Before you make it public

Everything here is already public on each member's LeetCode profile, but this
repo **collects it, timestamps it and ranks it** — which is a different thing.

What the project does about it:

- No LeetCode handle is committed anywhere. The board, `config.json` and the data
  files use codenames and opaque ids; the mapping lives in a git-ignored file and
  an Actions secret.
- The board does not link to anyone's profile.
- The GraphQL query does not ask for `realName`, so a real name never even arrives.
- `add.py` requires a display name rather than defaulting to one.
- **Only two data files exist, and both are bounded.** `today.json` holds the
  problem lists for today and is replaced tomorrow, never appended to.
  `history.json` is numbers only — per person per day, how many problems and the
  difficulty split, plus one tag histogram for the whole group — and drops the
  oldest day as each new one lands. Nothing accumulates.
- **A dated list of which problems someone solved, with timestamps, is a record of
  when they were at their keyboard.** That list now lives for one day. A count does
  not carry the same thing, so counts are what the history keeps.

What it cannot do — worth being straight about:

- **The problem list is itself a fingerprint.** Anyone holding a shortlist of
  candidate profiles can match them against the board by hand. Codenames stop a
  search engine tying a handle to this page; they do not stop someone who already
  suspects who is in the group.
- **The repo owner is named** by the account and the commit authorship, which
  narrows that shortlist a lot.
- **History is not retroactive.** Anything committed before a change is still in
  the old commits, and public-repo commits are mirrored by third-party archives
  within the hour. Rewriting history removes it from here; nothing removes it from
  the mirrors.

So: **ask everyone first**, and if any of the above matters, make the repo private.
It works exactly the same — members need read access to see the board, free-tier
Actions minutes cover an hourly job with room to spare, and unlike codenames it
covers the history too. For a small group that is the better default.
