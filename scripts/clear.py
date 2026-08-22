"""Clear the data a template copy inherits. Run this once, before the first fetch.

    python3 scripts/clear.py

Empties the member list, deletes every snapshot and blanks the board. Keeps
data/problems.json, which is only a difficulty and tag cache.
"""

import board
from common import SNAP_DIR, load_config, save_config


def main():
    cfg = load_config()
    snaps = sorted(SNAP_DIR.glob("*.json"))
    handles = [m["handle"] for m in cfg["members"]]

    if not handles and not snaps:
        print("Already clear.")
        return

    print(f"Drop members : {', '.join(handles) or 'none'}")
    print(f"Delete       : {len(snaps)} snapshot(s)")
    try:
        agreed = input("Proceed? [y/N]: ").strip().lower() in ("y", "yes")
    except EOFError:
        agreed = False
    if not agreed:
        print("Cancelled.")
        return

    cfg["members"] = []
    save_config(cfg)
    for path in snaps:
        path.unlink()
    board.update_readme(cfg)

    print("\nCleared. Set `timezone` in config.json, then run scripts/add.py.")


if __name__ == "__main__":
    main()
