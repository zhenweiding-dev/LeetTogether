"""Compute the board and write it into the README marker block.

Metrics come from AC events bucketed by day in cfg's timezone. A single snapshot
only carries the 20 most recent ACs; the union across snapshots grows the
reachable range over time. Dates outside that range are "no data", kept distinct
from "zero solved".
"""

import html
from collections import Counter, defaultdict
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
    load_snapshots,
    local_date,
    local_now,
    tags_of,
)

WINDOW = 14
WEEK = 7



def collect(handle, snapshots, cfg):
    """Returns (day_events, intervals).

    day_events -- {date: {slug: {"title", "ts"}}}
    intervals  -- [(start, end)] covered ranges; start None reaches back to the beginning
    """
    day_events = defaultdict(dict)
    intervals = []

    for snap_date, snap in snapshots:
        m = (snap.get("members") or {}).get(handle)
        if not m or not m.get("ok"):
            continue

        recent = m.get("recent_ac") or []
        for s in recent:
            date = local_date(s["ts"], cfg)
            prev = day_events[date].get(s["slug"])
            # same problem twice in one day counts once; keep the earliest time
            if prev is None or s["ts"] < prev["ts"]:
                day_events[date][s["slug"]] = {"title": s["title"], "ts": s["ts"]}

        # hitting the cap means older records were truncated
        truncated = m.get("recent_truncated", len(recent) >= lc.RECENT_LIMIT)
        if not truncated:
            intervals.append((None, snap_date))
        elif recent:
            intervals.append((min(local_date(s["ts"], cfg) for s in recent), snap_date))

    return day_events, intervals


def is_covered(date, intervals):
    return any(
        (start is None or start <= date) and date <= end for start, end in intervals
    )


def day_count(date, day_events, intervals):
    """Problems solved that day; None when outside coverage (no data, not zero)."""
    if date in day_events:
        return len(day_events[date])
    return 0 if is_covered(date, intervals) else None


def spark(counts):
    out = []
    for c in counts:
        if c is None:
            out.append(theme.NO_DATA)
        else:
            out.append(next(ch for hi, ch in theme.SPARK_LEVELS if c <= hi))
    return " ".join(out)


def streak_of(day_events, intervals, today):
    """Returns (consecutive days, whether coverage cut it short).

    Not having submitted yet today is not a break.
    """
    cur = datetime.strptime(today, "%Y-%m-%d").date()
    anchor = None
    for back in (0, 1):
        d = cur - timedelta(days=back)
        if (day_count(d.isoformat(), day_events, intervals) or 0) >= 1:
            anchor = d
            break
    if anchor is None:
        return 0, False

    count = 0
    while True:
        c = day_count(anchor.isoformat(), day_events, intervals)
        if c is None:
            return count, True  # hit the coverage edge, real streak may be longer
        if c < 1:
            return count, False  # confirmed break
        count += 1
        anchor -= timedelta(days=1)


def window_stats(dates, day_events, intervals, problems, weights):
    """Problems and weighted points in a window. partial means it spans no-data days."""
    probs = score = 0
    partial = False
    for d in dates:
        c = day_count(d, day_events, intervals)
        if c is None:
            partial = True
            continue
        probs += c
        for slug in day_events.get(d, {}):
            score += weights.get(difficulty_of(problems, slug).lower(), 0)
        if c >= lc.RECENT_LIMIT:
            partial = True  # one day filled the cap, more may be unfetched
    return probs, score, partial


def window_slugs(dates, day_events):
    """Slugs in the window; a re-solve on another day counts again, as the counts do."""
    return [slug for d in dates for slug in day_events.get(d, {})]


def tag_counts(slugs, problems):
    """[(tag, count)] by count descending, ties alphabetical."""
    counts = Counter()
    for slug in slugs:
        counts.update(tags_of(problems, slug))
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


def diff_line(slugs, problems):
    """This week's split by difficulty, in Easy/Medium/Hard order."""
    counts = Counter(difficulty_of(problems, s) for s in slugs)
    items = [
        theme.DIFF_LINE_ITEM.format(
            name=theme.DIFF_WORDS.get(d.lower(), d), count=counts[d]
        )
        for d in theme.DIFF_ORDER
        if counts.get(d)
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


def build_rows(cfg, snapshots, problems, today):
    latest = snapshots[-1][1]
    weights = cfg["score_weights"]
    rows, broken = [], []

    for m in cfg["members"]:
        handle = m["handle"]
        cur = (latest.get("members") or {}).get(handle)
        if not cur or not cur.get("ok"):
            broken.append(
                (
                    m.get("name") or handle,
                    handle,
                    (cur or {}).get("error", theme.ERR_NOT_FETCHED),
                )
            )
            continue

        day_events, intervals = collect(handle, snapshots, cfg)
        streak, streak_limited = streak_of(day_events, intervals, today)
        w_probs, w_score, w_partial = window_stats(
            days_back(today, WEEK), day_events, intervals, problems, weights
        )
        t_probs, t_score, t_partial = window_stats(
            [today], day_events, intervals, problems, weights
        )
        counts = [day_count(d, day_events, intervals) for d in days_back(today, WINDOW)]
        acs = sorted(
            (dict(slug=s, **v) for s, v in day_events.get(today, {}).items()),
            key=lambda a: a["ts"],
        )

        rows.append(
            {
                "name": cur.get("name") or handle,
                "handle": handle,
                "streak": streak,
                "streak_limited": streak_limited,
                "today": t_probs,
                "today_score": t_score,
                "today_partial": t_partial,
                "week": w_probs,
                "week_partial": w_partial,
                "week_score": w_score,
                "total": cur["solved"]["all"],  # sort tiebreaker only
                "stale": bool(cur.get("stale")),
                "spark": spark(counts),
                "acs": acs,
                "week_slugs": window_slugs(days_back(today, WEEK), day_events),
                "done_today": t_probs >= 1,
            }
        )

    # Today's points decide the rank; the rest only break ties, which happens a
    # lot early in the day when nobody has submitted yet.
    rows.sort(
        key=lambda r: (-r["today_score"], -r["week_score"], -r["streak"], -r["total"])
    )
    return rows, broken


def previous_ranks(cfg, snapshots, problems, today):
    """handle -> rank on the previous day's board; empty if that day has no snapshot."""
    prev = (
        datetime.strptime(today, "%Y-%m-%d").date() - timedelta(days=1)
    ).isoformat()
    if not any(d == prev for d, _ in snapshots):
        return {}
    rows, _ = build_rows(cfg, snapshots, problems, prev)
    return {r["handle"]: i for i, r in enumerate(rows, 1)}


def rank_move(handle, rank, prev_ranks):
    """Marker for a rank change since yesterday; blank when new or unchanged."""
    was = prev_ranks.get(handle)
    if was is None or was == rank:
        return ""
    return f" {theme.UP}" if rank < was else f" {theme.DOWN}"


def render(cfg, snapshots, problems, unreadable=()):
    now = local_now(cfg)
    today = now.strftime("%Y-%m-%d")

    if not snapshots:
        return theme.EMPTY_DATA + "\n"

    rows, broken = build_rows(cfg, snapshots, problems, today)
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

        prev_ranks = previous_ranks(cfg, snapshots, problems, today)
        ranking = []
        for i, r in enumerate(rows, 1):
            streak = theme.STREAK_CAPPED if r["streak_limited"] else theme.STREAK
            member = theme.MEMBER_CELL.format(
                rank=theme.MEDALS[i - 1] if i <= len(theme.MEDALS) else code(i),
                name=f'<a href="https://leetcode.com/u/{esc(r["handle"])}/">'
                f"{code(esc(r['name']))}</a>",
                move=rank_move(r["handle"], i, prev_ranks),
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
                    code(streak.format(days=r["streak"])),
                    code(r["spark"]),
                ]
            )
        legend = theme.LEGEND.format(
            easy=w["easy"],
            medium=w["medium"],
            hard=w["hard"],
            window=WINDOW,
            no_data=theme.NO_DATA,
        )
        out.append(
            table(
                [h.format(window=WINDOW) for h in theme.RANK_HEADERS],
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
        detail = []
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
            pairs = tag_counts([a["slug"] for a in r["acs"]], problems)
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

            detail.append(
                [code(esc(r["name"])), theme.PROBLEM_JOIN.join(lines), chips]
            )
        out.append(
            table(
                theme.DETAIL_HEADERS,
                theme.DETAIL_ALIGNS,
                detail,
                widths=theme.DETAIL_WIDTHS,
            )
        )
        out.append("")

    week_slugs = [s for r in rows for s in r["week_slugs"]]
    tags = tag_counts(week_slugs, problems)
    if tags:
        out.append(theme.HEAD_TAGS)
        out.append("")
        out.append(diff_line(week_slugs, problems))
        out.append("")
        out.append(tag_line(tags))
        out.append("")

    if broken:
        out.append(theme.HEAD_BROKEN)
        out.append("")
        for name, handle, err in broken:
            out.append(
                theme.BROKEN_ROW.format(handle=handle, name=name, error=err)
            )
        out.append("")

    stamp = theme.STAMP.format(
        when=now.strftime("%Y-%m-%d %H:%M"),
        tz=cfg["timezone"],
        days=len(snapshots),
    )
    out.append(f"<sub>{stamp}</sub>")
    return "\n".join(out).rstrip() + "\n"


def update_readme(cfg):
    snapshots, unreadable = load_snapshots()
    board = render(cfg, snapshots, load_problems(), unreadable)
    text = README.read_text(encoding="utf-8")

    if MARK_START not in text or MARK_END not in text:
        raise SystemExit(f"README is missing the {MARK_START} / {MARK_END} markers")

    head, rest = text.split(MARK_START, 1)
    _, tail = rest.split(MARK_END, 1)
    README.write_text(
        f"{head}{MARK_START}\n\n{board}\n{MARK_END}{tail}", encoding="utf-8"
    )
