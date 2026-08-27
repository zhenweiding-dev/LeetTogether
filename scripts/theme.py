"""Every string, glyph and icon the board renders. Tweak copy here, not in board.py.

`{...}` placeholders are filled by board.py; a template without placeholders is
used as-is. Tag names must match LeetCode's topicTags exactly.
"""

# --- empty states -----------------------------------------------------------

EMPTY_DATA = "_No data yet. Run `python3 scripts/update.py`._"
EMPTY_MEMBERS = "_No members yet. Run `python3 scripts/add.py`._"
ERR_NOT_FETCHED = "not fetched"

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
    "This week",
    "Streak",
    "Last {window} days",
]
RANK_ALIGNS = ["left"] + ["center"] * (len(RANK_HEADERS) - 1)  # names left

MEDALS = ["🥇", "🥈", "🥉"]
UP, DOWN = "🔺", "🔻"
MEMBER_CELL = "{rank} {name}{move}"  # rank lives in the member cell to save a column

STREAK = "🔥 {days}"
STREAK_CAPPED = "🔥 {days}+"  # coverage ran out, the real streak may be longer
TODAY_CELL = "{solved} ✅丨{points} pts"
WEEK_CELL = "{solved} ✅丨<b>{points} pts</b>"
AT_LEAST = "≥{value}"

# Daily volume glyphs: (upper bound, glyph), first match wins.
SPARK_LEVELS = [(0, "·"), (2, "▁"), (4, "▃"), (7, "▅"), (10**9, "▇")]
NO_DATA = "░"

LEGEND = (
    "🔺🔻 rank change since yesterday · <b>+</b> and <b>≥</b> mean at least<br>"
    "💡 <b>Scoring</b> Easy ×{easy} · Medium ×{medium} · Hard ×{hard} — "
    "<b>✅</b> problems solved, <b>pts</b> the same weighted by difficulty<br>"
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
PROBLEM_ITEM = "{num} {link}"
PROBLEM_JOIN = "<br>"
PROBLEM_LIMIT = 20
PROBLEM_MORE = "…"
# Tags are budgeted by width, not by count: "Array" and "Dynamic Programming"
# are wildly different sizes, so a fixed count makes the cell either half empty
# or twice as tall as the problem list. Roughly how many characters of tag text
# fit on one line of the Tags column.
TAG_CHARS_PER_LINE = 26
TAG_MORE = "…"

# --- weekly tags ------------------------------------------------------------

HEAD_TAGS = "## 🏷️ Tags this week"
TAG_CHIP = "{tag}丨{count}"  # <code> chip, used in the per-member Tags column
TAG_LINE_ITEM = "{icon} {tag} **{count}**"  # weekly blockquote
TAG_LINE_JOIN = " 丨 "
TAG_LINE = "> {items}"

# --- failures and footer ----------------------------------------------------

HEAD_BROKEN = "## ⚠️ Fetch failed"
BROKEN_ROW = "- `{handle}` ({name}) - {error}"
STAMP = "🕒 Updated {when} ({tz}) · {days} day(s) of history"

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
    "Design": "🏗️",
    "Binary Search": "🔍",
    "String Matching": "🔎",
    "Bracket Sequences": "🪆",
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
    "Recursion": "🔁",
    "Divide and Conquer": "⚔️",
    "Tree": "🌳",
    "Binary Tree": "🌲",
    "Binary Search Tree": "🎄",
    "N-ary Tree": "🌴",
    "Trie": "🌿",
    "Cartesian Tree": "🌱",
    "Segment Tree": "🎋",
    "Binary Indexed Tree": "🎍",
    "Range Minimum/Maximum Query": "📏",
    "Minimum Spanning Tree": "🌉",
    "Graph": "🕸️",
    "Graph Theory": "🕸️",
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
