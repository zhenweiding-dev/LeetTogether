"""Every string, glyph and icon the board renders. Tweak copy here, not in board.py.

`{...}` placeholders are filled by board.py; a template without placeholders is
used as-is. Tag names must match LeetCode's topicTags exactly.
"""

# --- empty states -----------------------------------------------------------

EMPTY_DATA = "_No data yet. Run `python3 scripts/update.py`._"
EMPTY_MEMBERS = "_No members yet. Run `python3 scripts/add.py`._"
ERR_NOT_FETCHED = "not fetched"
ERR_NO_HANDLE = "no LeetCode handle configured for this id"

# --- today's progress line --------------------------------------------------

# Shown above everything when a fetch went wrong; omitted entirely when all is well.
WARN = "> ⚠️ {items}"
WARN_FAILED = "**{names}** could not be fetched"
WARN_STALE = "**{names}** showing earlier data from today"
WARN_UNREADABLE = "**{names}** could not be parsed, that day is missing"
WARN_JOIN = " · "

HEAD_BOARD = "## 🏆 Leaderboard"
STATUS = "{icon} **{done}/{total} submitted today**"
STATUS_PENDING = " · pending: {names}"

# Share of the group that submitted today -> icon, first match wins.
PROGRESS = [(1.0, "🎉"), (0.5, "🔥"), (0.0, "⏳")]
PROGRESS_NONE = "💤"

# --- leaderboard ------------------------------------------------------------

RANK_HEADERS = [
    "Member",
    "Today",
    "Last {week} days",
    "Streak",
    "Last {window} days",
]
RANK_ALIGNS = ["left"] + ["center"] * (len(RANK_HEADERS) - 1)  # names left

MEDALS = ["🥇", "🥈", "🥉"]
UP, DOWN = "🔺", "🔻"
MEMBER_CELL = "{rank} {name}{move}"  # rank lives in the member cell to save a column

STREAK = "{icon} {days}"
STREAK_CAPPED = "{icon} {days}+"  # window ran out, the real streak may be longer

# Streak ladder: (upper bound in days, icon), first match wins.
#
# Front-loaded on purpose — an upgrade every day or two in the first week, when
# quitting is easiest. Icons climb spark -> star -> moon filling up -> sun, so the
# glyph alone shows progress without reading the number.
#
# Light tops out at the sun; there is no brighter same-family glyph. Past 37 days
# it goes rarer rather than brighter — rainbow, unicorn, crown — which is the right
# axis for a long streak. Those tiers also need the repo to have that much history
# before anyone can reach them, so they stay aspirational for a long time.
STREAK_LEVELS = [
    (0, "😴"),
    (1, "✨"),
    (3, "💫"),
    (5, "⭐"),
    (6, "🌟"),
    (9, "🌙"),
    (13, "🌒"),
    (19, "🌓"),
    (29, "🌔"),
    (36, "🌕"),
    (49, "☀️"),
    (99, "🌈"),
    (364, "🦄"),
    (10**9, "👑"),
]
TODAY_CELL = "{solved} ✅丨{points} pts"
WEEK_CELL = "{solved} ✅丨<b>{points} pts</b>"
AT_LEAST = "≥{value}"

# Daily volume glyphs: (upper bound, glyph), first match wins.
SPARK_LEVELS = [(0, "·"), (2, "▁"), (4, "▃"), (7, "▅"), (10**9, "▇")]
NO_DATA = "░"

# Words, not coloured dots: any circle in a README reads as a status alert.
DIFF_WORDS = {"easy": "Easy", "medium": "Med", "hard": "Hard"}
DIFF_FALLBACK = "?"

# 🔺🔻 needs no explaining, so it is left out. {ladder} is generated from
# STREAK_LEVELS rather than written out here, so the two can never drift apart.
LADDER_JOIN = "&nbsp; "  # Markdown collapses runs of spaces
LEGEND = (
    "🔥 <b>Streak</b> {ladder}<br>"
    "💡 <b>Scoring</b> Easy ×{easy} · Med ×{medium} · Hard ×{hard} — "
    "<b>✅</b> solved, <b>pts</b> weighted points<br>"
    "📊 <b>Last {window} days</b> <code>·</code> no submission · "
    "<code>{no_data}</code> no data"
)

# --- today's submissions ----------------------------------------------------

HEAD_DETAIL = "## 📅 Today's submissions"
DETAIL_HEADERS = ["Member", "Problems", "Tags"]
DETAIL_ALIGNS = ["left", "left", "left"]
# Left to itself the browser hands Tags the most room, because a row of inline
# chips asks for more width than a stack of lines. Pin the split instead.
DETAIL_WIDTHS = ["15%", "55%", "30%"]

# Plain lines rather than an <ol>: the number is LeetCode's own, and dropping the
# list reclaims its indent for the titles.
PROBLEM_ITEM = "{diff} {num} {link}"
PROBLEM_JOIN = "<br>"
PROBLEM_LIMIT = 20
PROBLEM_MORE = "…"
# Tags are budgeted by width, not by count: "Array" and "Dynamic Programming"
# are wildly different sizes, so a fixed count makes the cell either half empty
# or twice as tall as the problem list. Measured off the rendered board, not
# derived — each chip's padding costs more room than its characters suggest.
TAG_CHARS_PER_LINE = 18
TAG_MORE = "…"

# --- weekly tags ------------------------------------------------------------

HEAD_TAGS = "## 🏷️ Tags, last {week} days"
DIFF_LINE_ITEM = "{name} {count}"
TAG_CHIP = "{tag}丨{count}"  # <code> chip, used in the per-member Tags column
# Weekly blockquote, each item inside a <code> chip. A third of the tags are
# usually one-offs, so those keep their place but drop the "丨1" noise.
TAG_LINE_ITEM = "{icon} {tag}丨{count}"
TAG_LINE_ITEM_BARE = "{icon} {tag}"
TAG_MIN_COUNT = 2
TAG_LINE_JOIN = " "
TAG_LINE = "> {items}"

# --- failures and footer ----------------------------------------------------

HEAD_BROKEN = "## ⚠️ Fetch failed"
BROKEN_ROW = "- `{id}` ({name}) - {error}"
STAMP = "🕒 Updated {when} ({tz}) · {days} day(s) of history{rate}"
# Measured from the run log each day carries, not a number written down once.
# Dropped entirely until there is a logged day to measure.
STAMP_RATE = " · ⏱️ {pct}% of hourly runs landed"

# --- tag icons --------------------------------------------------------------

TAG_FALLBACK = "⚪"
TAG_ICONS = {
    "Array": "🔢",
    "String": "🧵",
    "Hash Table": "🗂️",
    "Hash Function": "#️⃣",
    "Rolling Hash": "🎡",
    "Dynamic Programming": "🧩",
    "Memoization": "🗒️",
    "Math": "➗",
    "Number Theory": "🔟",
    "Geometry": "📐",
    "Combinatorics": "🎰",
    "Brainteaser": "🧠",
    "Probability and Statistics": "🎯",
    "Greedy": "🤑",
    "Sorting": "📶",
    "Merge Sort": "🪡",
    "Bucket Sort": "🪣",
    "Radix Sort": "🧺",
    "Counting Sort": "🗳️",
    "Tournament Sort": "🏆",
    "Quickselect": "⚡",
    "Counting": "🧮",
    "Prefix Sum": "➕",
    "Enumeration": "📋",
    "Simulation": "🎮",
    "Meet in the Middle": "🧲",
    "Knapsack Problem": "🎒",
    "0-1 Knapsack": "🧳",
    "Design": "🏗️",
    "Binary Search": "🔍",
    "String Matching": "🔎",
    "Bracket Sequences": "🪆",
    "Longest Common Subsequence": "🧬",
    "Two Pointers": "↔️",
    "Sliding Window": "🪟",
    "Line Sweep": "🧹",
    "Sweep Line": "🧹",
    "Bit Manipulation": "🎛️",
    "Bitmask": "🎭",
    "Matrix": "🧇",
    "Depth-First Search": "🤿",
    "Breadth-First Search": "🌊",
    "Backtracking": "↩️",
    "Algorithm X": "✖️",
    "Dancing Links": "💃",
    "Recursion": "🔁",
    "Divide and Conquer": "⚔️",
    "Tree": "🌳",
    "Binary Tree": "🌲",
    "Binary Search Tree": "🎄",
    "N-ary Tree": "🌴",
    "Trie": "🌿",
    "Cartesian Tree": "🌱",
    "DP on Trees": "🪵",
    "Segment Tree": "🎋",
    "Binary Indexed Tree": "🎍",
    "Range Minimum/Maximum Query": "📏",
    "Minimum Spanning Tree": "🌉",
    "Graph": "🕸️",
    "Graph Theory": "🕸️",
    "Planar Graph": "📄",
    "Directed Acyclic Graph": "🪃",
    "Topological Sort": "🧭",
    "Shortest Path": "🛣️",
    "Eulerian Circuit": "🔃",
    "Strongly Connected Component": "🧷",
    "Biconnected Component": "🔩",
    "Union Find": "🤝",
    "Union-Find": "🤝",
    "Stack": "🥞",
    "Monotonic Stack": "🧱",
    "Queue": "🎟️",
    "Monotonic Queue": "🚋",
    "Heap (Priority Queue)": "⛰️",
    "Heap": "⛰️",
    "Linked List": "🔗",
    "Doubly-Linked List": "⛓️",
    "Ordered Set": "📚",
    "Ordered Map": "🗺️",
    "Suffix Array": "🪢",
    "Data Stream": "🚰",
    "Iterator": "➡️",
    "Randomized": "🪙",
    "Game Theory": "🎲",
    "Minimax": "♟️",
    "Reservoir Sampling": "🎣",
    "Rejection Sampling": "🚫",
    "Interactive": "💬",
    "Concurrency": "⚙️",
    "Database": "🗄️",
    "Shell": "🐚",
}
