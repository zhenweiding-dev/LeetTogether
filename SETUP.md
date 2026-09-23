# Set up your own

↩ [Back to the board](README.md)

One README, no server, no database, no login, no API key. A GitHub Action reads
everyone's public LeetCode profile hourly and rewrites the table on the front page.

## Quick start

1. [Use this template](https://github.com/zhenweiding-dev/LeetTogether/generate)

2. Wipe this group's data, then set `timezone` in `config.json` to your
   [IANA name](https://en.wikipedia.org/wiki/List_of_tz_database_time_zones).

   ```bash
   python3 scripts/clear.py
   ```

3. Add everyone. Takes a username or a profile URL, verifies it, and asks for the
   codename to show on the board.

   ```bash
   python3 scripts/add.py
   ```

   Three destinations: the codename goes to `config.json`, the real handle to
   `handles.local.json` which git ignores, and the mapping into the `LC_HANDLES`
   secret the Action reads. It checks for the GitHub CLI before asking anything —
   offering to install it if Homebrew is around — and if the secret still cannot
   be written it says why and prints the one command to finish by hand. The local
   files are saved either way.

4. `git push`

The Action needs nothing installed — Python standard library only. Setup uses the
[GitHub CLI](https://cli.github.com) for that one secret. Nothing for the others to
do either: a normal LeetCode account is readable as is.

GitHub drops a lot of scheduled runs, so the board can sit several hours stale. If
that bothers you, [a more reliable schedule](#a-more-reliable-schedule) at the
bottom swaps the trigger for an external cron.

## Reading the board

| Mark | Means |
|---|---|
| `🔺` `🔻` | moved up or down since yesterday |
| `·` `░` | that day had no submission / there is no record of it |
| `≥21` | at least 21; the window does not reach far enough back to be sure |
| `12+` | streak is at least 12, possibly longer |
| `⚠️` above the table | a fetch went wrong; absent when all is well |
| `😴 ✨ 💫 ⭐ 🌟 🌙 🌒 🌓 🌔 🌕 ☀️ 🌈 🦄 👑` | streak ladder, front-loaded so it moves in the first week |

Ranking is **today's points** — it resets every morning and lifetime totals never
count, so nobody is ever out of reach. Ties go to the last 7 days, then the streak.
Weights are Easy 1 / Medium 3 / Hard 6, so grinding Easies does not move you up.

Both windows are rolling, not calendar: `Last 7 days` is today plus the six before
it, and does not reset on Mondays. A problem solved twice in one day counts once;
picked up again another day it counts again.

Somebody added today gets their recent days filled in from the solves LeetCode
still returns — a few days for a heavy solver, weeks for a light one. Older days
stay `░`: only 20 solves come back per fetch, and nothing else reports a day the
way the board counts one.

## When a fetch fails

| Error | Cause |
|---|---|
| `no LeetCode handle configured for this id` | in `config.json` but not in the secret; `gh secret set LC_HANDLES < handles.local.json` |
| `not fetched` | just added, and the Action has not run since |
| `That user does not exist.` | wrong username |
| `no permission to check the calendar.` | official or special account, rare |
| `request failed: ...` | network, timeout or TLS — retried, then reported |

Nothing already recorded is lost. If someone has good numbers from earlier today
the board keeps them and says so at the top; only a member with no data at all
drops out of the table.

## Files

| Path | Purpose |
|---|---|
| `config.json` | codenames and ids, timezone, scoring weights |
| `handles.local.json` | id → LeetCode handle — **git-ignored, never commit it** |
| `data/history.json` | 16 days of numbers, keyed by id — bounded, never grows |
| `data/today.json` | today's problem lists, replaced each day |
| `data/problems.json` | slug → number, difficulty, tags — queried once per problem |
| `scripts/theme.py` | every label, emoji and threshold the board renders |
| `scripts/board.py` | metrics and rendering |
| `scripts/update.py` | what the Action runs |

## Privacy

Ask your group before making the repo public. Handles are never committed — the
board shows codenames, and the mapping stays in the `LC_HANDLES` secret. Only
today's problem list is kept; older days are counts. A private repo works exactly
the same, and members only need read access.

## Notes

- Under **Settings → Actions → General**, new repos default the token to read-only.
  The workflow asks for `contents: write` — leave that block in or the commit 403s.
- The Action makes one commit per day and amends it on later runs, so it
  force-pushes. Branch protection on `main` will block that.
- GitHub drops scheduled runs when its queue is busy. The board's footer prints the
  measured hit rate, so you can see how often yours land.
- Scheduled workflows stop after 60 days of repository inactivity; GitHub emails
  first, and one manual run brings them back.
- `leetcode.com` only. `leetcode.cn` is a separate account system with a different
  GraphQL schema.

## A more reliable schedule

This repo measured 29% of its hourly runs landing, with three to five hour gaps.
Nothing is lost unless someone solves more than 20 problems inside one gap, but
the board sits stale. An external cron calling the `workflow_dispatch` API fixes
it, and the workflow already accepts that trigger.

1. Make a [fine-grained token](https://github.com/settings/personal-access-tokens/new):
   one year, `Only select repositories` → this repo, and `Repository permissions
   → Actions → Read and write`. Nothing else. It is shown once, and it never goes
   in the repo.

2. Point a cron service at the workflow every 30 minutes —
   [cron-job.org](https://cron-job.org) is free. Method `POST`, body
   `{"ref":"main"}`, and three headers:

   ```
   https://api.github.com/repos/OWNER/REPO/actions/workflows/daily.yml/dispatches
   ```

   | Header | Value |
   |---|---|
   | `Authorization` | `Bearer` + a space + the token |
   | `Accept` | `application/vnd.github+json` |
   | `Content-Type` | `application/json` |

   Its Test run should answer `204`, and the Actions tab should get a run straight
   away. `401` is a mistyped token; `403` or `404` is a missing permission or the
   wrong repo. Turn on its failure notifications, and leave the workflow's own
   `schedule` in as a backup — `ref:` on the checkout step is what stops a queued
   run from colliding with it.

The cron service stores that token in plain text. `Actions: Read and write` can
trigger, cancel and re-run workflows and delete their logs — it cannot push code,
read secrets or edit the workflow.

The footer's hit rate climbs over the next fortnight rather than at once, and it
will not reach 100%: it counts hours that saw a run, so twice an hour earns no
extra credit.
