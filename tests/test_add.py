"""add.py: handle parsing, id allocation, and the secret-write preflight."""

import builtins
import json

import add
import common
from conftest import write_json


# --- parse_handle ------------------------------------------------------------


def test_parse_handle_bare_username():
    assert add.parse_handle("alice") == "alice"


def test_parse_handle_trailing_slash_and_whitespace():
    assert add.parse_handle("  alice/  ") == "alice"


def test_parse_handle_profile_url_forms():
    assert add.parse_handle("https://leetcode.com/u/alice/") == "alice"
    assert add.parse_handle("leetcode.com/profile/bob") == "bob"
    assert add.parse_handle("www.leetcode.com/u/carol") == "carol"
    assert add.parse_handle("https://leetcode.com/u/alice/?tab=submissions") == "alice"


def test_parse_handle_u_prefix_only():
    assert add.parse_handle("u/dave") == "dave"


def test_parse_handle_problem_page_is_rejected():
    # A /problems/ URL is a content page, not a profile: returning its first
    # segment would send a doomed lookup for the handle "problems".
    assert add.parse_handle("https://leetcode.com/problems/two-sum/") == ""
    assert add.parse_handle("https://leetcode.com/contest/weekly-400/") == ""


def test_parse_handle_junk_rejected():
    assert add.parse_handle("!!!") == ""
    assert add.parse_handle("has space") == ""
    assert add.parse_handle("ümlaut") == ""


def test_parse_handle_dashes_and_underscores_ok():
    assert add.parse_handle("alice-bob") == "alice-bob"
    assert add.parse_handle("under_score") == "under_score"


def test_parse_handle_bare_domain_is_empty():
    assert add.parse_handle("leetcode.com") == ""
    assert add.parse_handle("https://leetcode.com/u/") == ""


# --- next_id -----------------------------------------------------------------


def test_next_id_first_free():
    assert add.next_id({"members": []}) == "m1"
    assert add.next_id({"members": [{"id": "m1"}, {"id": "m3"}]}) == "m2"
    assert add.next_id({"members": [{"id": "m1"}, {"id": "m2"}]}) == "m3"


# --- prompts -----------------------------------------------------------------


def test_prompts_consumes_args_then_stdin(monkeypatch):
    monkeypatch.setattr(builtins, "input", lambda *a: (_ for _ in ()).throw(EOFError()))
    assert list(add.prompts(["a", "b"])) == ["a", "b"]


def test_prompts_interactive_then_eof(monkeypatch):
    answers = iter(["x", "y"])

    def fake_input(_):
        try:
            return next(answers)
        except StopIteration:
            raise EOFError()

    monkeypatch.setattr(builtins, "input", fake_input)
    assert list(add.prompts([])) == ["x", "y"]


# --- preflight ---------------------------------------------------------------


class FakeRun:
    """subprocess.run stand-in: per-command behavior, scriptable."""

    def __init__(self, results):
        self.results = results  # {"git": (rc, stdout), "gh auth": rc, ...}
        self.calls = []

    def __call__(self, cmd, **kw):
        key = " ".join(cmd)
        self.calls.append(key)
        if key not in self.results:
            raise AssertionError(f"unexpected command: {key}")
        r = self.results[key]
        if isinstance(r, int):
            return type("R", (), {"returncode": r})()
        rc, stdout = r
        return type("R", (), {"returncode": rc, "stdout": stdout})()


def good_git():
    return {"git remote": (0, "origin\n")}


def test_preflight_git_missing(monkeypatch):
    def run(cmd, **kw):
        raise FileNotFoundError("git")

    monkeypatch.setattr(add.subprocess, "run", run)
    reason, cost, fix = add.preflight()
    assert "git is not installed" in reason


def test_preflight_not_a_repo(monkeypatch):
    fake = FakeRun({"git remote": (1, "")})
    monkeypatch.setattr(add.subprocess, "run", fake)
    reason, _, _ = add.preflight()
    assert "not a git repository" in reason


def test_preflight_no_remote(monkeypatch):
    fake = FakeRun({"git remote": (0, "")})
    monkeypatch.setattr(add.subprocess, "run", fake)
    reason, _, _ = add.preflight()
    assert "no remote" in reason


def test_preflight_no_gh_no_brew(monkeypatch):
    fake = FakeRun(good_git())
    monkeypatch.setattr(add.subprocess, "run", fake)
    monkeypatch.setattr(add.shutil, "which", lambda name: None)
    reason, cost, fix = add.preflight()
    assert "gh is not installed" in reason
    assert "Action cannot read the new handles" in cost  # secret can be copied by hand


def test_preflight_install_gh_with_brew(monkeypatch):
    fake = FakeRun(good_git() | {"brew install gh": 0, "gh auth status": 0})
    monkeypatch.setattr(add.subprocess, "run", fake)
    wheres = iter([None, "/opt/homebrew/bin/brew", "/opt/homebrew/bin/gh"])
    monkeypatch.setattr(
        add.shutil, "which",
        lambda name: next(wheres, None) if name in ("brew", "gh") else None,
    )
    monkeypatch.setattr(builtins, "input", lambda *a: "y")
    assert add.preflight() is None
    assert "brew install gh" in fake.calls


def test_preflight_gh_auth_fails(monkeypatch):
    fake = FakeRun(good_git() | {"gh auth status": 1})
    monkeypatch.setattr(add.subprocess, "run", fake)
    monkeypatch.setattr(add.shutil, "which", lambda name: "/usr/local/bin/gh" if name == "gh" else None)
    reason, cost, fix = add.preflight()
    assert "not logged in" in reason


# --- set_secret --------------------------------------------------------------


def test_set_secret_writes_via_stdin(paths, monkeypatch):
    monkeypatch.setattr(add, "HANDLES_PATH", paths / "handles_path.json")  # bound import
    write_json(paths / "handles_path.json", {"m1": "alice"})
    seen = {}

    def fake_run(cmd, stdin=None, **kw):
        seen["cmd"] = cmd
        seen["data"] = stdin.read().decode()
        return type("R", (), {"returncode": 0, "stderr": ""})()

    monkeypatch.setattr(add.subprocess, "run", fake_run)
    assert add.set_secret() is None
    assert seen["cmd"] == ["gh", "secret", "set", common.HANDLES_ENV]
    assert json.loads(seen["data"]) == {"m1": "alice"}  # piped, never argv


def test_set_secret_reports_last_stderr_line(paths, monkeypatch):
    monkeypatch.setattr(add, "HANDLES_PATH", paths / "handles_path.json")
    write_json(paths / "handles_path.json", {"m1": "alice"})
    r = type("R", (), {"returncode": 1, "stderr": "boom\nTry: gh auth login\n"})()
    monkeypatch.setattr(add.subprocess, "run", lambda cmd, **kw: r)
    assert add.set_secret() == "Try: gh auth login"


def test_set_secret_gh_missing(paths, monkeypatch):
    monkeypatch.setattr(add, "HANDLES_PATH", paths / "handles_path.json")
    write_json(paths / "handles_path.json", {"m1": "alice"})

    def run(cmd, **kw):
        raise FileNotFoundError("gh")

    monkeypatch.setattr(add.subprocess, "run", run)
    assert add.set_secret() == "gh is not installed"