# LeetTogether

<!-- LEADERBOARD:START -->

🎉 **1/1 submitted today**

<table>
<thead>
<tr>
<th align="center"><div align="center">Rank</div></th>
<th align="center"><div align="center">Member</div></th>
<th align="center"><div align="center">Streak</div></th>
<th align="center"><div align="center">Today</div></th>
<th align="center"><div align="center">This week</div></th>
<th align="center"><div align="center">Last 14 days</div></th>
</tr>
</thead>
<tbody>
<tr>
<td align="center">🥇</td>
<td align="center"><code>zhenwei</code></td>
<td align="center"><code>6+</code></td>
<td align="center"><code>1 ✅丨3 pts</code></td>
<td align="center"><code>≥21 ✅丨<b>≥57 pts</b></code></td>
<td align="center"><code>░ ░ ░ ░ ░ ░ ░ ░ ▁ ▁ ▇ ▁ ▃ ▁</code></td>
</tr>
<tr><td colspan="6"><sub>· Scoring Easy×1 / Medium×3 / Hard×6 · Last 14 days: <code>·</code> none, <code>░</code> no data</sub></td></tr>
</tbody>
</table>

**Today's submissions**

<table>
<thead>
<tr>
<th align="center"><div align="center">Member</div></th>
<th align="left"><div align="left">Problems</div></th>
<th align="left"><div align="center">Tags</div></th>
</tr>
</thead>
<tbody>
<tr>
<td align="center"><code>zhenwei</code></td>
<td align="left"><ol><li><a href="https://leetcode.com/problems/subsets/"><code>Subsets</code></a></li></ol></td>
<td align="left"><code>Array丨1</code> <code>Backtracking丨1</code> <code>Bit Manipulation丨1</code></td>
</tr>
</tbody>
</table>

**Tags this week**

<code>🌳 Tree丨18</code> <code>🌲 Binary Tree丨15</code> <code>🔢 Array丨8</code> <code>🎄 Binary Search Tree丨7</code> <code>🤿 Depth-First Search丨7</code> <code>⚔️ Divide and Conquer丨5</code> <code>🌊 Breadth-First Search丨4</code> <code>🥞 Stack丨4</code> <code>🗂️ Hash Table丨3</code> <code>↩️ Backtracking丨2</code> <code>🌱 Cartesian Tree丨2</code> <code>🧱 Monotonic Stack丨2</code> <code>🔍 Binary Search丨1</code> <code>🎛️ Bit Manipulation丨1</code>

<sub>Updated 2026-08-22 01:09 (America/Los_Angeles) · 2 day(s) of history</sub>

<!-- LEADERBOARD:END -->

---

## Usage

```bash
python3 scripts/add.py       # add members, then refresh
python3 scripts/update.py    # refresh the board above on its own

# Standard library only, nothing to install.
# GitHub Actions runs update.py twice a day (~12:00 and ~23:50 local time).
```

Adding someone is the only manual step: `add.py` refreshes the board when it
finishes, and the daily runs take over from there.

## Adding members

- `add.py` takes a username or profile URL, verifies it, asks for a display name,
  and writes it to [config.json](config.json)
- Add several in a row; blank input finishes
- On exit it runs the same fetch as `update.py`, so the board already shows them
- Or pass it in directly:

```bash
python3 scripts/add.py leetcode.com/u/alice/
```

Accepted forms: `https://leetcode.com/u/alice/`, `leetcode.com/alice`,
`leetcode.com/profile/alice/`, `alice`.

A normal account needs no privacy changes. Only two failures exist:

| Error | Cause |
|---|---|
| `That user does not exist.` | wrong username |
| `no permission to check the calendar.` | official or special account, rare |

## Scoring

1. Ranked by **points this week**, not lifetime total; difficulty weights are configurable
2. Days are bucketed by `timezone`
3. The same problem twice in one day counts once; re-solved on another day it counts again

> Weights and timezone both live in [config.json](config.json)

## Files

| Path | Purpose |
|---|---|
| [config.json](config.json) | members, timezone, scoring weights |
| `data/snapshots/<date>.json` | daily snapshot: solved counts plus the 20 most recent ACs; re-running the same day overwrites |
| `data/problems.json` | slug to difficulty and tags, queried once per problem |
| [scripts/lc.py](scripts/lc.py) | LeetCode GraphQL client |
| [scripts/board.py](scripts/board.py) | metrics and board rendering |
