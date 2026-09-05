"""Add a member: enter a username or profile URL, verify it, name it, save it.

    python3 scripts/add.py                       # interactive
    python3 scripts/add.py leetcode.com/u/alice/ # or pass it in

Writes config.json (codename and an opaque id, safe to commit), handles.local.json
(id -> real handle, git-ignored), and the LC_HANDLES secret the Action reads.

Never touches the board or the data files. Those belong to the Action, which runs
every hour, so a local rewrite would only race it for the same lines.
"""

import re
import shutil
import subprocess
import sys

import lc
import theme
from common import (
    HANDLES_ENV,
    HANDLES_PATH,
    load_config,
    load_handles,
    save_config,
    save_handles,
)


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


# Two different sizes of problem, so they say two different things. Missing git or
# a repo that is not on GitHub means the Action does not exist at all and nothing
# will ever update on its own. A missing gh only means this one secret has to be
# copied over by hand.
NO_AUTOMATION = "the hourly Action cannot run at all, so the board never updates on its own"
NO_SYNC = "the Action cannot read the new handles, so the board shows them as missing"


def install_gh():
    """Offer to install the GitHub CLI with Homebrew. Returns whether it is now there.

    Homebrew only. Guessing at another platform's package manager and running it
    with sudo is not a script's business, and guessing wrong is worse than one
    manual install.
    """
    if not shutil.which("brew"):
        return False  # the caller's message already says where to get it
    print(f"\nThe GitHub CLI is missing — it is what writes the {HANDLES_ENV} secret.")
    try:
        agreed = input("  install it now with Homebrew? [y/N]: ").strip().lower()
    except EOFError:
        return False
    if agreed not in ("y", "yes"):
        return False
    print()
    subprocess.run(["brew", "install", "gh"])  # visible: it is not a quick one
    return bool(shutil.which("gh"))


def preflight():
    """What stops the secret being written: (short reason, consequence, how to fix).

    Checked before a single username is asked for. The same problem found at the
    end costs the whole roster typed in again, and the point of writing the secret
    here at all is that nobody has to remember a second step.
    """
    # One call covers both ways gh can fail to find the repo: it exits non-zero
    # outside a work tree, and prints nothing when the tree has no remote.
    try:
        remotes = subprocess.run(["git", "remote"], capture_output=True, text=True)
    except FileNotFoundError:
        return ("git is not installed", NO_AUTOMATION,
                "macOS: xcode-select --install · else https://git-scm.com")
    if remotes.returncode:
        return ("this folder is not a git repository", NO_AUTOMATION,
                "git init, then gh repo create --source=. --private --push")
    if not remotes.stdout.strip():
        return ("this repository has no remote", NO_AUTOMATION,
                "gh repo create --source=. --private --push")

    if not shutil.which("gh"):
        if not install_gh():
            return ("gh is not installed", NO_SYNC,
                    "brew install gh · else https://cli.github.com")

    # Worded here rather than passed through from gh, whose phrasing for this moves
    # between versions and whose last stderr line is often just the suggested command.
    if subprocess.run(["gh", "auth", "status"], capture_output=True).returncode:
        return ("gh is not logged in", NO_SYNC, "gh auth login")
    return None


def set_secret():
    """Push the whole mapping into the LC_HANDLES secret. Returns None, or why not.

    Written once at the end rather than per member, because the secret holds the
    whole file. Piped on stdin, never passed as an argument: anything in argv is
    readable by every process on the machine, and this is the one moment real
    handles leave it.
    """
    try:
        with HANDLES_PATH.open("rb") as f:
            done = subprocess.run(
                ["gh", "secret", "set", HANDLES_ENV],
                stdin=f,
                capture_output=True,
                text=True,
            )
    except FileNotFoundError:
        return "gh is not installed"
    if done.returncode:
        err = done.stderr.strip().splitlines()
        return err[-1] if err else "gh failed"
    return None


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

    blocked = preflight()
    if blocked:
        reason, cost, fix = blocked
        print(f"\n{reason} — {cost}.")
        print(f"Fix with:  {fix}")
        print("Members are still saved locally either way.\n")

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

    print(f"Added {len(added)}: {', '.join(added)}\n")
    print("  config.json          codenames only, commit it")
    print(f"  {HANDLES_PATH.name}   real handles, git-ignored")

    failed = (blocked[0] if blocked else None) or set_secret()
    if failed:
        print(f"  {HANDLES_ENV} secret    NOT set: {failed}\n")
        print(f"The board will show `{theme.ERR_NO_HANDLE}` for them")
        print("until the secret catches up. Once the above is sorted:\n")
        print(f"  gh secret set {HANDLES_ENV} < {HANDLES_PATH.name}\n")
    else:
        print(f"  {HANDLES_ENV} secret    updated, {len(handles)} member(s)\n")
        print("Commit config.json; the hourly Action takes it from there.")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print()
