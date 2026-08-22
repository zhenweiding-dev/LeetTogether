"""Every string, glyph and icon the board renders. Tweak copy here, not in board.py.

`{...}` placeholders are filled by board.py; a template without placeholders is
used as-is. Tag names must match LeetCode's topicTags exactly.
"""

# --- empty states -----------------------------------------------------------

EMPTY_DATA = "_No data yet. Run `python3 scripts/update.py`._"
EMPTY_MEMBERS = "_No members yet. Run `python3 scripts/add.py`._"
ERR_NOT_FETCHED = "not fetched"

# --- today's progress line --------------------------------------------------

STATUS = "{icon} **{done}/{total} submitted today**"
STATUS_PENDING = " · pending: {names}"

# Share of the group that submitted today -> icon, first match wins.
PROGRESS = [(1.0, "🎉"), (0.5, "🔥"), (0.0, "⏳")]
PROGRESS_NONE = "💤"

# --- leaderboard ------------------------------------------------------------

RANK_HEADERS = [
    "Rank",
    "Member",
    "Streak",
    "Today",
    "This week",
    "Last {window} days",
]
RANK_ALIGNS = ["center"] * len(RANK_HEADERS)

MEDALS = ["🥇", "🥈", "🥉"]
UP, DOWN = "🔺", "🔻"

STREAK = "{days}"
STREAK_CAPPED = "{days}+"  # coverage ran out, the real streak may be longer
TODAY_CELL = "{solved} ✅丨{points} pts"
WEEK_CELL = "{solved} ✅丨<b>{points} pts</b>"
AT_LEAST = "≥{value}"

# Daily volume glyphs: (upper bound, glyph), first match wins.
SPARK_LEVELS = [(0, "·"), (2, "▁"), (4, "▃"), (7, "▅"), (10**9, "▇")]
NO_DATA = "░"

LEGEND = (
    "· Scoring Easy×{easy} / Medium×{medium} / Hard×{hard} "
    "· Last {window} days: <code>·</code> none, <code>{no_data}</code> no data"
)

# --- today's submissions ----------------------------------------------------

HEAD_DETAIL = "**Today's submissions**"
DETAIL_HEADERS = ["Member", "Problems", "Tags"]
DETAIL_HEAD_ALIGNS = ["center", "left", "center"]
DETAIL_ALIGNS = ["center", "left", "left"]  # wrapping cells read better left

# --- weekly tags ------------------------------------------------------------

HEAD_TAGS = "**Tags this week**"
TAG_CHIP = "{tag}丨{count}"
TAG_CHIP_ICON = "{icon} {tag}丨{count}"

# --- failures and footer ----------------------------------------------------

HEAD_BROKEN = "**Fetch failed**"
BROKEN_ROW = "- `{handle}` ({name}) - {error}"
STAMP = "Updated {when} ({tz}) · {days} day(s) of history"

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
    "Design": "🏗️",
    "Binary Search": "🔍",
    "String Matching": "🔎",
    "Two Pointers": "↔️",
    "Sliding Window": "🪟",
    "Line Sweep": "🧹",
    "Bit Manipulation": "🎛️",
    "Bitmask": "🎭",
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
    "Stack": "🥞",
    "Monotonic Stack": "🧱",
    "Queue": "🎟️",
    "Monotonic Queue": "🚋",
    "Heap (Priority Queue)": "⛰️",
    "Linked List": "🔗",
    "Doubly-Linked List": "⛓️",
    "Ordered Set": "📚",
    "Suffix Array": "🪢",
    "Data Stream": "🚰",
    "Iterator": "➡️",
    "Randomized": "🪙",
    "Game Theory": "🎲",
    "Reservoir Sampling": "🎣",
    "Rejection Sampling": "🚫",
    "Interactive": "💬",
    "Concurrency": "⚙️",
    "Database": "🗄️",
    "Shell": "🐚",
}
