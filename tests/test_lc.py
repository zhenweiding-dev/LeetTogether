"""lc.py: the GraphQL client — retry semantics and response parsing, fully offline.

urllib.request.urlopen is monkeypatched per test; no socket ever opens.
"""

import json

import pytest

import lc


class FakeResponse:
    def __init__(self, payload):
        self._payload = payload

    def read(self):
        return self._payload

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False


def install_fake_opener(monkeypatch, side_effect):
    """side_effect: callable(*args, **kwargs) -> FakeResponse, or raises.

    Returns (calls, slept): the urlopen invocations and every backoff sleep.
    """
    calls = []
    slept = []

    def opener(*args, **kwargs):
        calls.append((args, kwargs))
        return side_effect(*args, **kwargs)

    def sleep(s):
        slept.append(s)

    monkeypatch.setattr(lc.urllib.request, "urlopen", opener)
    monkeypatch.setattr(lc.time, "sleep", sleep)
    return calls, slept


def ok_response(data):
    return FakeResponse(json.dumps(data).encode())


def http_error(code):
    """A urlopen stand-in that *raises* HTTPError, like the real one does."""

    def _raise(*args, **kwargs):
        raise lc.urllib.error.HTTPError("url", code, "err", {}, None)

    return _raise


def test_query_success(monkeypatch):
    payload = {"data": {"matchedUser": None}}
    calls, _ = install_fake_opener(monkeypatch, lambda *a, **k: ok_response(payload))
    assert lc.query("gql", {"handle": "x"}) == payload
    assert len(calls) == 1
    req = calls[0][0][0]
    assert req.full_url == lc.ENDPOINT
    assert json.loads(req.data) == {"query": "gql", "variables": {"handle": "x"}}


def test_query_retries_retryable_then_raises(monkeypatch):
    _, slept = install_fake_opener(monkeypatch, http_error(500))
    with pytest.raises(RuntimeError, match="request failed"):
        lc.query("gql", {})
    assert len(slept) == 2  # waited between the 3 attempts


def test_query_no_retry_on_permanent_code(monkeypatch):
    _, slept = install_fake_opener(monkeypatch, http_error(404))
    with pytest.raises(RuntimeError):
        lc.query("gql", {})
    assert slept == []  # 404 is permanent


def test_query_retries_urlerror(monkeypatch):
    def fail(*a, **k):
        raise lc.urllib.error.URLError("boom")

    _, slept = install_fake_opener(monkeypatch, fail)
    with pytest.raises(RuntimeError, match="boom"):
        lc.query("gql", {})
    assert len(slept) == 2


def test_query_retries_on_bad_json(monkeypatch):
    def bad(*a, **k):
        return FakeResponse(b"{not json")

    _, slept = install_fake_opener(monkeypatch, bad)
    with pytest.raises(RuntimeError):
        lc.query("gql", {})
    assert len(slept) == 2


def test_query_succeeds_on_second_try(monkeypatch):
    payload = {"data": {"matchedUser": {"username": "u"}}}
    attempts = []

    def flaky(*a, **k):
        attempts.append(1)
        if len(attempts) == 1:
            raise lc.urllib.error.URLError("transient")
        return ok_response(payload)

    install_fake_opener(monkeypatch, flaky)
    assert lc.query("gql", {}) == payload
    assert len(attempts) == 2


def _user_payload(handle="alice", counts=None, recent=None):
    counts = counts or [("All", 10), ("Easy", 4), ("Medium", 5), ("Hard", 1)]
    return {
        "data": {
            "matchedUser": {
                "username": handle,
                "submitStats": {
                    "acSubmissionNum": [{"difficulty": d, "count": c} for d, c in counts]
                },
                "userCalendar": {"streak": 3},
            },
            "recentAcSubmissionList": recent or [],
        }
    }


def test_fetch_user_ok(monkeypatch):
    install_fake_opener(
        monkeypatch,
        lambda *a, **k: ok_response(
            _user_payload(
                recent=[
                    {"title": "Two Sum", "titleSlug": "twosum", "timestamp": "1790300000"},
                    {"title": "Old", "titleSlug": "old", "timestamp": "1789000000"},
                ]
            )
        ),
    )
    out = lc.fetch_user("alice")
    assert out["ok"] is True
    assert out["handle"] == "alice"
    assert out["solved"] == {"all": 10, "easy": 4, "medium": 5, "hard": 1}
    assert out["recent_ac"][0] == {"title": "Two Sum", "slug": "twosum", "ts": 1790300000}


def test_fetch_user_missing_user_reports_reason(monkeypatch):
    payload = {
        "data": {"matchedUser": None},
        "errors": [{"message": "That user does not exist."}],
    }
    install_fake_opener(monkeypatch, lambda *a, **k: ok_response(payload))
    out = lc.fetch_user("nobody")
    assert out == {"ok": False, "error": "That user does not exist."}


def test_fetch_user_missing_fields_default_to_zero(monkeypatch):
    install_fake_opener(
        monkeypatch,
        lambda *a, **k: ok_response(
            {"data": {"matchedUser": {"username": "u", "submitStats": {"acSubmissionNum": []},
                                      "userCalendar": {}}, "recentAcSubmissionList": None}}
        ),
    )
    out = lc.fetch_user("u")
    assert out["ok"] is True
    assert out["solved"] == {"all": 0, "easy": 0, "medium": 0, "hard": 0}
    assert out["recent_ac"] == []


def test_fetch_question_parses(monkeypatch):
    payload = {
        "data": {
            "question": {
                "questionFrontendId": "1",
                "title": "Two Sum",
                "difficulty": "Easy",
                "topicTags": [{"name": "Array"}, {"name": "Hash Table"}],
            }
        }
    }
    install_fake_opener(monkeypatch, lambda *a, **k: ok_response(payload))
    assert lc.fetch_question("twosum") == {
        "frontend_id": "1",
        "difficulty": "Easy",
        "tags": ["Array", "Hash Table"],
    }


def test_fetch_question_missing_returns_none(monkeypatch):
    install_fake_opener(monkeypatch, lambda *a, **k: ok_response({"data": {"question": None}}))
    assert lc.fetch_question("garbage") is None


def test_ssl_context_fallback_when_trust_store_empty(monkeypatch):
    class EmptyTrust:
        def cert_store_stats(self):
            return {"x509_ca": 0}

        def load_verify_locations(self, where):
            assert "certifi" in where  # proxied through import

    def fake_default():
        return EmptyTrust()

    pytest.importorskip("certifi")
    monkeypatch.setattr(lc.ssl, "create_default_context", fake_default)
    ctx = lc._ssl_context()
    assert ctx is not None