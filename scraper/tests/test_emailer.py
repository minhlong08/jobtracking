import json

import httpx
import pytest

from tracker import emailer


def test_send_posts_to_resend(monkeypatch):
    monkeypatch.setenv("RESEND_API_KEY", "re_test")
    monkeypatch.setenv("EMAIL_TO", "me@example.com")
    monkeypatch.delenv("EMAIL_FROM", raising=False)
    seen = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["url"] = str(request.url)
        seen["auth"] = request.headers["Authorization"]
        seen["body"] = json.loads(request.content)
        return httpx.Response(200, json={"id": "abc"})

    emailer.send("3 new roles", "<p>hi</p>", transport=httpx.MockTransport(handler))
    assert seen["url"] == emailer.RESEND_URL
    assert seen["auth"] == "Bearer re_test"
    assert seen["body"] == {
        "from": emailer.DEFAULT_FROM, "to": ["me@example.com"], "subject": "3 new roles", "html": "<p>hi</p>",
    }


def test_send_raises_on_rejection(monkeypatch):
    monkeypatch.setenv("RESEND_API_KEY", "re_test")
    monkeypatch.setenv("EMAIL_TO", "me@example.com")
    transport = httpx.MockTransport(lambda r: httpx.Response(403, json={"message": "invalid key"}))
    with pytest.raises(RuntimeError, match="403"):
        emailer.send("s", "h", transport=transport)
