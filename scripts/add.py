"""Add a member: enter a username or profile URL, verify it, name it, save it.

    python3 scripts/add.py                       # interactive
    python3 scripts/add.py leetcode.com/u/alice/ # or pass it in

Writes two files and no others. config.json gets a codename and an opaque id, safe
to commit; handles.local.json gets the id -> real handle mapping and is ignored by
git. The board and the data files are left to the Action, so a local run can never
collide with it on a generated file.
"""

import re
import sys

import lc
from common import HANDLES_PATH, load_config, load_handles, save_config, save_handles


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


def next_id(cfg):
    """m1, m2, ... — deliberately says nothing about who the member is."""
    used = {m.get("id") for m in cfg["members"]}
    n = 1
    while f"m{n}" in used:
        n += 1
    return f"m{n}"


def main():
    cfg = load_config()
    handles = load_handles()
    known = {h.lower() for h in handles.values()}
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

        # This is the name the public board will show, so it defaults to nothing:
        # neither the real name nor the handle should slip out by pressing Enter.
        try:
            name = input("  display name (shown on the public board): ").strip()
        except EOFError:
            name = ""
        if not name:
            print("  skipped: a display name is required\n")
            continue

        mid = next_id(cfg)
        cfg["members"].append({"id": mid, "name": name})
        handles[mid] = handle
        known.add(handle.lower())
        save_config(cfg)  # save as we go so an interrupt loses nothing
        save_handles(handles)
        added.append(name)
        print(f"  saved as {mid}\n")

    if not added:
        print("No changes.")
        return

    print(f"Added {len(added)}: {', '.join(added)}")
    print(f"\nconfig.json holds only codenames — commit it. {HANDLES_PATH.name} holds")
    print("the real handles and is git-ignored; paste its contents into the")
    print("LC_HANDLES repo secret so the Action can fetch:")
    print("\n  gh secret set LC_HANDLES < handles.local.json\n")
    print("Then `gh workflow run daily.yml`, or wait for the hourly run.")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print()
