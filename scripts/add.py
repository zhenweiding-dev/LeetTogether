"""Add a member: enter a username or profile URL, verify it, name it, save to config.

    python3 scripts/add.py                       # interactive
    python3 scripts/add.py leetcode.com/u/alice/ # or pass it in
"""

import re
import sys

import lc
from common import load_config, save_config


def parse_handle(raw):
    """Extract the handle from a username or any form of profile URL."""
    s = re.sub(r"^https?://", "", raw.strip())
    s = s.split("?")[0].split("#")[0]
    if "/" not in s:
        return s

    parts = [p for p in s.split("/") if p]
    if parts and "leetcode" in parts[0].lower():
        parts = parts[1:]  # domain
    if parts and parts[0] in ("u", "profile"):
        parts = parts[1:]  # /u/ or /profile/ prefix
    return parts[0] if parts else ""


def prompts(args):
    """Consume argv first, then switch to interactive input."""
    yield from args
    while True:
        try:
            yield input("Username or profile URL (blank to finish): ")
        except EOFError:
            return


def main():
    cfg = load_config()
    known = {m["handle"].lower() for m in cfg["members"]}
    added = []

    for raw in prompts(sys.argv[1:]):
        if not raw.strip():
            break

        if "leetcode.cn" in raw.lower():
            print("  skipped: leetcode.cn link, this project only supports .com\n")
            continue

        handle = parse_handle(raw)
        if not handle:
            print("  could not parse a username\n")
            continue
        if handle.lower() in known:
            print(f"  {handle} already added\n")
            continue

        print(f"  checking {handle}...")
        try:
            data = lc.fetch_user(handle)
        except RuntimeError as exc:
            print(f"  request failed: {exc}\n")
            continue
        if not data["ok"]:
            print(f"  {data['error']}\n")
            continue

        handle = data["handle"]  # canonical casing from the API
        s = data["solved"]
        print(
            f"  ok - {s['all']} solved "
            f"(E {s['easy']} / M {s['medium']} / H {s['hard']}), "
            f"{len(data['recent_ac'])} recent ACs"
        )

        default = data["real_name"] or handle
        try:
            name = input(f"  display name [{default}]: ").strip() or default
        except EOFError:
            name = default

        cfg["members"].append({"handle": handle, "name": name})
        known.add(handle.lower())
        save_config(cfg)  # save as we go so an interrupt loses nothing
        added.append(name)
        print("  written to config.json\n")

    if added:
        print(f"Added {len(added)}: {', '.join(added)}")
        print("Run `python3 scripts/update.py` to refresh the board.")
    else:
        print("No changes.")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print()
