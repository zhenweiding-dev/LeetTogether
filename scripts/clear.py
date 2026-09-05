"""Clear the data a template copy inherits. Run this once, before the first fetch.

    python3 scripts/clear.py

Empties the member list, deletes the history and today files and blanks the
board. Keeps data/problems.json, which is only a difficulty and tag cache.
"""

import board
from common import HANDLES_PATH, HISTORY_PATH, TODAY_PATH, load_config, save_config


def main():
    cfg = load_config()
    data = [p for p in (HISTORY_PATH, TODAY_PATH) if p.exists()]
    names = [m.get("name") or m.get("id", "?") for m in cfg["members"]]

    if not names and not data and not HANDLES_PATH.exists():
        print("Already clear.")
        return

    print(f"Drop members : {', '.join(names) or 'none'}")
    print(f"Delete       : {', '.join(p.name for p in data) or 'nothing'}")
    if HANDLES_PATH.exists():
        print(f"Delete       : {HANDLES_PATH.name}")
    try:
        agreed = input("Proceed? [y/N]: ").strip().lower() in ("y", "yes")
    except EOFError:
        agreed = False
    if not agreed:
        print("Cancelled.")
        return

    cfg["members"] = []
    save_config(cfg)
    for path in data:
        path.unlink()
    HANDLES_PATH.unlink(missing_ok=True)
    board.update_readme(cfg)

    print("\nCleared. Set `timezone` in config.json, then run scripts/add.py.")


if __name__ == "__main__":
    main()
