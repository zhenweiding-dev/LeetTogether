"""Compute the board and write it into the README marker block.

Two files feed this. history.json is numbers only: per member per day, how many
problems and the difficulty split, plus one tag histogram for the whole group;
it keeps RETAIN days and drops the rest. today.json holds the one problem list the
project keeps, and anything about the current run. A day the window no longer
covers is "no data", kept distinct from "zero solved".
"""

import html
from collections import Counter
from datetime import datetime, timedelta

import lc
import theme
from common import (
    MARK_END,
    MARK_START,
    README,
    days_back,
    difficulty_of,
    frontend_id_of,
    load_problems,
    load_history,
    load_today,
    local_date,
    local_now,
    tags_of,
    tz_of,
)

WINDOW = 14
WEEK = 7
# Days kept in history.json. Not WINDOW: the board also renders yesterday's
# ranking to work out the 🔺🔻 arrows, which reaches one day further back, and
# solved_deltas needs the day before that to take a difference against.
RETAIN = WINDOW + 2
# Hourly slots the run log needs before the hit rate is worth printing. Below this
# it is one lucky run reading 100%, which says nothing about the scheduler.
RATE_MIN_SLOTS = 12



def day_events(mid, detail, cfg, on_date):
    """{slug: {"title", "ts"}} for one day, out of today.json.

    The only problem list the project keeps. Every other day exists as the four
    numbers in day_counts and nothing more.
    """
    out = {}
    m = (detail.get("members") or {}).get(mid)
    for s in (m or {}).get("recent_ac") or []:
        if local_date(s["ts"], cfg) != on_date:
            continue
        prev = out.get(s["slug"])
        # same problem twice in one day counts once; keep the earliest time
        if prev is None or s["ts"] < prev["ts"]:
            out[s["slug"]] = {"title": s["title"], "ts": s["ts"]}
    return out


def day_counts(slugs, problems):
    """One member's day: how many problems, split by difficulty.

    All that survives of a day once its problem list is gone. Everything the
    leaderboard shows for a past day is a sum over these four numbers.
    """
    out = {"count": len(slugs), "easy": 0, "medium": 0, "hard": 0}
    for slug in slugs:
        d = difficulty_of(problems, slug).lower()
        if d in out:
            out[d] += 1
    return out


def tag_histogram(slugs, problems):
    """{tag: count} over a set of slugs.

    Stored once per day for the whole group, not per member: the weekly tag
    section sums everyone together, so a per-member copy would be four times the
    bytes for a number nothing reads.
    """
    counts = Counter()
    for slug in slugs:
        counts.update(tags_of(problems, slug))
    return dict(sorted(counts.items()))


def member_days(history, mid):
    """{date: that day's record for this member}, ascending. Absent = no data."""
    return {
        date: m
        for date, entry in sorted(history.items())
        if (m := (entry.get("members") or {}).get(mid))
    }


def day_stats(days):
    """{date: day counts} for the days that have them."""
    return {date: m["day"] for date, m in days.items() if m.get("day")}


def day_count(date, days):
    """Problems solved that day; None when the window does not hold it."""
    agg = days.get(date)
    return agg["count"] if agg else None


def spark(counts):
    out = []
    for c in counts:
        if c is None:
            out.append(theme.NO_DATA)
        else:
            out.append(next(ch for hi, ch in theme.SPARK_LEVELS if c <= hi))
    return " ".join(out)


def streak_of(days, today):
    """Returns (consecutive days, whether coverage cut it short).

    Not having submitted yet today is not a break.
    """
    cur = datetime.strptime(today, "%Y-%m-%d").date()
    anchor = None
    for back in (0, 1):
        d = cur - timedelta(days=back)
        if (day_count(d.isoformat(), days) or 0) >= 1:
            anchor = d
            break
    if anchor is None:
        return 0, False

    count = 0
    while True:
        c = day_count(anchor.isoformat(), days)
        if c is None:
            return count, True  # hit the coverage edge, real streak may be longer
        if c < 1:
            return count, False  # confirmed break
        count += 1
        anchor -= timedelta(days=1)


def stored_streak(days, today):
    """Yesterday's stored end-of-day streak, or None if that day is not in history."""
    prev = (
        datetime.strptime(today, "%Y-%m-%d").date() - timedelta(days=1)
    ).isoformat()
    return (days.get(prev) or {}).get("streak")


def streak_with_history(days, today, active, prev_eod):
    """Returns (display, end_of_day, coverage_limited).

    The window only reaches back so far, so the streak is carried forward in it
    instead of being re-derived from scratch. The derived value is still used as a
    floor: a stored count can be stale-low when the last run of that day landed
    before the member's last submission of it.
    """
    derived, limited = streak_of(days, today)
    if prev_eod is None:  # no snapshot for yesterday, nothing to carry
        return derived, (derived if active else 0), limited
    display = max(derived, prev_eod + 1 if active else prev_eod)
    return display, (display if active else 0), False


def solved_deltas(days):
    """{date: {easy/medium/hard: newly solved}} from consecutive lifetime totals.

    Immune to the 20-item recent_ac cap, which is the point: on a day that filled
    the cap this is what the day really was. Two things it is not — it cannot see a
    re-solve, and it credits the day whose record caught the rise, so a day the
    Action never ran rolls into the next one.
    """
    out, prev = {}, None
    for date, m in days.items():
        cur = m.get("solved") or {}
        if prev is not None:
            out[date] = {
                k: max(0, cur.get(k, 0) - prev.get(k, 0))
                for k in ("easy", "medium", "hard")
            }
        prev = cur
    return out


DIFFS = ("easy", "medium", "hard")


def window_stats(dates, days, weights, deltas):
    """Problems and weighted points in a window. partial means it spans no-data days."""
    probs = score = 0
    partial = False
    for d in dates:
        agg = days.get(d)
        if agg is None:
            partial = True
            continue
        c = agg["count"]
        pts = sum(weights.get(k, 0) * agg.get(k, 0) for k in DIFFS)
        if c >= lc.RECENT_LIMIT:
            # The fetch window truncated at 20, but the lifetime totals moved by
            # the real amount that day, so read the day off those instead.
            by_diff = deltas.get(d)
            if not by_diff:
                partial = True  # nothing to compare against, usually day one
            elif sum(by_diff.values()) > c:
                c = sum(by_diff.values())
                pts = sum(weights.get(k, 0) * n for k, n in by_diff.items())
        probs += c
        score += pts
    return probs, score, partial


def window_tags(dates, history):
    """{tag: count} over the window, summed across the whole group."""
    counts = Counter()
    for d in dates:
        counts.update((history.get(d) or {}).get("tags") or {})
    return counts


def window_diffs(dates, days):
    """{easy/medium/hard: n} over the window."""
    counts = Counter()
    for d in dates:
        if agg := days.get(d):
            counts.update({k: agg.get(k, 0) for k in DIFFS})
    return counts


def ranked(counts):
    """A Counter as [(key, n)] by count descending, ties alphabetical."""
    return sorted(counts.items(), key=lambda kv: (-kv[1], kv[0]))


def num(value, partial):
    return theme.AT_LEAST.format(value=value) if partial else str(value)


def esc(text):
    return html.escape(str(text), quote=True)


def code(value):
    """GitHub strips style attributes; <code> is the only way to shrink text."""
    return f"<code>{value}</code>"


def tag_chips(pairs):
    """`tag丨count` code chips, for the per-member Tags column."""
    return " ".join(
        code(theme.TAG_CHIP.format(tag=esc(tag), count=n)) for tag, n in pairs
    )


def diff_line(counts):
    """Split by difficulty over the window, in Easy/Medium/Hard order."""
    items = [
        theme.DIFF_LINE_ITEM.format(name=theme.DIFF_WORDS[k], count=counts[k])
        for k in DIFFS
        if counts.get(k)
    ]
    return theme.TAG_LINE.format(items=theme.TAG_LINE_JOIN.join(items))


def tag_line(pairs):
    """The weekly tag distribution as one blockquote line of chips.

    Every tag keeps its place; the ones seen only once show no count.
    """
    items = theme.TAG_LINE_JOIN.join(
        code(
            (
                theme.TAG_LINE_ITEM
                if n >= theme.TAG_MIN_COUNT
                else theme.TAG_LINE_ITEM_BARE
            ).format(
                icon=theme.TAG_ICONS.get(tag, theme.TAG_FALLBACK),
                tag=esc(tag),
                count=n,
            )
        )
        for tag, n in pairs
    )
    return theme.TAG_LINE.format(items=items)


def streak_ladder():
    """Each tier as `icon` plus the day it starts at, straight from STREAK_LEVELS."""
    out, low = [], 0
    for hi, icon in theme.STREAK_LEVELS:
        out.append(f"{icon}{low}")
        low = hi + 1
    return theme.LADDER_JOIN.join(out)


def run_rate(history, now):
    """Percent of hourly slots a run actually landed in, or None if not measurable.

    GitHub drops scheduled runs under load, so this is measured rather than quoted:
    every run marks its local hour in the day's record. Days from before the log
    existed are skipped, not counted as misses. The first logged day starts at
    its first run and today ends at the current hour, so neither partial day counts
    hours that were never eligible.
    """
    logged = [(d, (e.get("run_hours") or "")) for d, e in sorted(history.items())]
    logged = [(d, mask) for d, mask in logged if "1" in mask]
    today = now.strftime("%Y-%m-%d")

    hits = slots = 0
    for i, (date, mask) in enumerate(logged):
        lo = mask.index("1") if i == 0 else 0  # nothing before the log began counts
        hi = now.hour if date == today else 23  # the rest of today has not happened
        slots += max(0, hi - lo + 1)
        hits += mask.count("1")
    if slots < RATE_MIN_SLOTS:
        return None
    return min(100, round(100 * hits / slots))


def progress_icon(done, total):
    """Emoji for how much of the group has submitted today."""
    if not total or not done:
        return theme.PROGRESS_NONE
    share = done / total
    return next(icon for cut, icon in theme.PROGRESS if share >= cut)


def table(headers, aligns, rows, footer=None, widths=None):
    """Render an HTML table.

    HTML rather than a Markdown pipe table, for the two things pipe tables cannot
    do: a footer spanning every column, and line breaks inside a cell. The cost is
    that Markdown does not apply inside cells, so links are emitted as <a>.
    """
    if len(headers) != len(aligns):
        raise ValueError(f"headers({len(headers)}) and aligns({len(aligns)}) differ")

    def cell(tag, value, align, width=None):
        attrs = f' align="{align}"' if align else ""
        attrs += f' width="{width}"' if width else ""
        return f"<{tag}{attrs}>{value}</{tag}>"

    out = ["<table>", "<thead>", "<tr>"]
    # headers always left; width on the header is enough to pin the column
    out += [
        cell("th", h, "left", w)
        for h, w in zip(headers, widths or [None] * len(headers))
    ]
    out += ["</tr>", "</thead>", "<tbody>"]
    for cells in rows:
        out.append("<tr>")
        out += [cell("td", c, a) for c, a in zip(cells, aligns)]
        out.append("</tr>")
    if footer:
        out.append(f'<tr><td colspan="{len(headers)}">{footer}</td></tr>')
    out += ["</tbody>", "</table>"]
    return "\n".join(out)


def build_rows(cfg, history, detail, problems, today):
    # Whether a fetch just failed is current-run state, so it comes from
    # today.json; history.json is only ever the numbers.
    latest = (history[max(history)].get("members") or {}) if history else {}
    failed = detail.get("failed") or {}
    stale = set(detail.get("stale") or ())
    weights = cfg["score_weights"]
    rows, broken = [], []

    for m in cfg["members"]:
        mid = m["id"]
        name = m.get("name") or mid
        cur = latest.get(mid)
        if mid in failed or not cur:
            broken.append((name, mid, failed.get(mid, theme.ERR_NOT_FETCHED)))
            continue

        mdays = member_days(history, mid)
        days = day_stats(mdays)
        deltas = solved_deltas(mdays)
        week = days_back(today, WEEK)
        w_probs, w_score, w_partial = window_stats(week, days, weights, deltas)
        t_probs, t_score, t_partial = window_stats([today], days, weights, deltas)
        streak, streak_eod, streak_limited = streak_with_history(
            days,
            today,
            active=t_probs >= 1,
            prev_eod=stored_streak(mdays, today),
        )
        counts = [day_count(d, days) for d in days_back(today, WINDOW)]
        acs = sorted(
            (dict(slug=s, **v) for s, v in day_events(mid, detail, cfg, today).items()),
            key=lambda a: a["ts"],
        )

        rows.append(
            {
                "name": name,
                "id": mid,
                "streak": streak,
                "streak_eod": streak_eod,  # what tomorrow carries forward
                "streak_limited": streak_limited,
                "today": t_probs,
                "today_score": t_score,
                "today_partial": t_partial,
                "week": w_probs,
                "week_partial": w_partial,
                "week_score": w_score,
                "total": cur["solved"]["all"],  # sort tiebreaker only
                "stale": mid in stale,
                "spark": spark(counts),
                "acs": acs,
                "week_diffs": window_diffs(week, days),
                "done_today": t_probs >= 1,
            }
        )

    # Today's points decide the rank; the rest only break ties, which happens a
    # lot early in the day when nobody has submitted yet.
    rows.sort(
        key=lambda r: (-r["today_score"], -r["week_score"], -r["streak"], -r["total"])
    )
    return rows, broken


def previous_ranks(cfg, history, detail, problems, today):
    """member id -> rank on the previous day's board; empty if that day is not held."""
    prev = (
        datetime.strptime(today, "%Y-%m-%d").date() - timedelta(days=1)
    ).isoformat()
    if prev not in history:
        return {}
    rows, _ = build_rows(cfg, history, detail, problems, prev)
    return {r["id"]: i for i, r in enumerate(rows, 1)}


def rank_move(mid, rank, prev_ranks):
    """Marker for a rank change since yesterday; blank when new or unchanged."""
    was = prev_ranks.get(mid)
    if was is None or was == rank:
        return ""
    return f" {theme.UP}" if rank < was else f" {theme.DOWN}"


def render(cfg, history, detail, problems, unreadable=()):
    now = local_now(cfg)
    today = now.strftime("%Y-%m-%d")

    if not history:
        return theme.EMPTY_DATA + "\n"

    rows, broken = build_rows(cfg, history, detail, problems, today)
    if not rows and not broken:
        return theme.EMPTY_MEMBERS + "\n"

    w = cfg["score_weights"]
    out = []

    # Anything wrong goes at the very top; the terminal is not the only reader.
    notes = []
    if unreadable:
        notes.append(theme.WARN_UNREADABLE.format(names=", ".join(unreadable)))
    if broken:
        notes.append(theme.WARN_FAILED.format(names=", ".join(n for n, _, _ in broken)))
    if stale := [r["name"] for r in rows if r["stale"]]:
        notes.append(theme.WARN_STALE.format(names=", ".join(stale)))
    if notes:
        out.append(theme.WARN.format(items=theme.WARN_JOIN.join(notes)))
        out.append("")

    # rows can be empty while broken is not: every fetch failed. Fall through so
    # the failures get reported instead of claiming there are no members.
    if rows:
        idle = [r["name"] for r in rows if not r["done_today"]]
        done = len(rows) - len(idle)
        line = theme.STATUS.format(
            icon=progress_icon(done, len(rows)), done=done, total=len(rows)
        )
        if idle:
            line += theme.STATUS_PENDING.format(names=", ".join(idle))
        out.append(theme.HEAD_BOARD)
        out.append("")
        out.append(line)
        out.append("")

        prev_ranks = previous_ranks(cfg, history, detail, problems, today)
        ranking = []
        for i, r in enumerate(rows, 1):
            tpl = theme.STREAK_CAPPED if r["streak_limited"] else theme.STREAK
            streak = tpl.format(
                icon=next(
                    i for hi, i in theme.STREAK_LEVELS if r["streak"] <= hi
                ),
                days=r["streak"],
            )
            # The display name only, never a link to the profile: the board should
            # not be the thing that ties a codename to a real LeetCode account.
            member = theme.MEMBER_CELL.format(
                rank=theme.MEDALS[i - 1] if i <= len(theme.MEDALS) else code(i),
                name=code(esc(r["name"])),
                move=rank_move(r["id"], i, prev_ranks),
            )
            ranking.append(
                [
                    member,
                    code(
                        theme.TODAY_CELL.format(
                            solved=num(r["today"], r["today_partial"]),
                            points=num(r["today_score"], r["today_partial"]),
                        )
                    ),
                    code(
                        theme.WEEK_CELL.format(
                            solved=num(r["week"], r["week_partial"]),
                            points=num(r["week_score"], r["week_partial"]),
                        )
                    ),
                    code(streak),
                    code(r["spark"]),
                ]
            )
        legend = theme.LEGEND.format(
            ladder=streak_ladder(),
            easy=w["easy"],
            medium=w["medium"],
            hard=w["hard"],
            window=WINDOW,
            no_data=theme.NO_DATA,
        )
        out.append(
            table(
                [h.format(window=WINDOW, week=WEEK) for h in theme.RANK_HEADERS],
                theme.RANK_ALIGNS,
                ranking,
                f"<sub>{legend}</sub>",
            )
        )
        out.append("")

    # by today's volume, not leaderboard rank: this table is scoped to today
    active = sorted(
        (r for r in rows if r["acs"]),
        key=lambda r: (-r["today"], -r["today_score"]),
    )
    if active:
        out.append(theme.HEAD_DETAIL)
        out.append("")
        detail_rows = []
        for r in active:
            lines = []
            for a in r["acs"][: theme.PROBLEM_LIMIT]:
                link = (
                    f'<a href="https://leetcode.com/problems/{esc(a["slug"])}/">'
                    f"{code(esc(a['title']))}</a>"
                )
                nid = frontend_id_of(problems, a["slug"])
                diff = difficulty_of(problems, a["slug"]).lower()
                word = theme.DIFF_WORDS.get(diff, theme.DIFF_FALLBACK)
                lines.append(
                    theme.PROBLEM_ITEM.format(
                        diff=code(word),
                        num=code(nid) if nid else "",
                        link=link,
                    )
                )
            if len(r["acs"]) > theme.PROBLEM_LIMIT:
                lines.append(theme.PROBLEM_MORE)

            # counted over everything today, but only as much tag text as the
            # problem list is tall, so neither cell towers over the other
            pairs = ranked(tag_histogram([a["slug"] for a in r["acs"]], problems))
            budget = len(lines) * theme.TAG_CHARS_PER_LINE
            shown, used = [], 0
            for tag, n in pairs:
                cost = len(tag) + len(str(n)) + 2  # "tag丨n" plus the gap
                if shown and used + cost > budget:
                    break
                shown.append((tag, n))
                used += cost
            chips = tag_chips(shown)
            if len(shown) < len(pairs):
                chips += f" {theme.TAG_MORE}"

            detail_rows.append(
                [code(esc(r["name"])), theme.PROBLEM_JOIN.join(lines), chips]
            )
        out.append(
            table(
                theme.DETAIL_HEADERS,
                theme.DETAIL_ALIGNS,
                detail_rows,
                widths=theme.DETAIL_WIDTHS,
            )
        )
        out.append("")

    tags = window_tags(days_back(today, WEEK), history)
    if tags:
        out.append(theme.HEAD_TAGS.format(week=WEEK))
        out.append("")
        out.append(diff_line(sum((r["week_diffs"] for r in rows), Counter())))
        out.append("")
        out.append(tag_line(ranked(tags)))
        out.append("")

    if broken:
        out.append(theme.HEAD_BROKEN)
        out.append("")
        for name, mid, err in broken:
            out.append(
                theme.BROKEN_ROW.format(id=mid, name=name, error=err)
            )
        out.append("")

    # The stored timestamp, not the render time: a run that finds nothing new
    # leaves both the data and this line untouched, so no commit is made.
    fetched = detail.get("fetched_at")
    when = (
        datetime.fromisoformat(fetched).astimezone(tz_of(cfg))
        if fetched
        else now
    ).strftime("%Y-%m-%d %H:%M")
    rate = run_rate(history, now)
    stamp = theme.STAMP.format(
        when=when,
        tz=cfg["timezone"],
        days=len(history),
        rate="" if rate is None else theme.STAMP_RATE.format(pct=rate),
    )
    out.append(f"<sub>{stamp}</sub>")
    return "\n".join(out).rstrip() + "\n"


def update_readme(cfg):
    """Rewrites the README and returns {member id: end-of-day streak} to persist."""
    stored, bad_history = load_history()
    detail, bad_today = load_today()
    history = stored.get("days") or {}
    unreadable = [n for n in (bad_history, bad_today) if n]
    problems = load_problems()
    board = render(cfg, history, detail, problems, unreadable)
    text = README.read_text(encoding="utf-8")

    if MARK_START not in text or MARK_END not in text:
        raise SystemExit(f"README is missing the {MARK_START} / {MARK_END} markers")

    head, rest = text.split(MARK_START, 1)
    _, tail = rest.split(MARK_END, 1)
    README.write_text(
        f"{head}{MARK_START}\n\n{board}\n{MARK_END}{tail}", encoding="utf-8"
    )

    if not history:
        return {}
    today = local_now(cfg).strftime("%Y-%m-%d")
    rows, _ = build_rows(cfg, history, detail, problems, today)
    return {r["id"]: r["streak_eod"] for r in rows}
