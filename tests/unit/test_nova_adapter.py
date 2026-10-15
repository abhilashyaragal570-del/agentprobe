import json

import httpx
import pytest

from agentprobe.adapters.nova import NovaAdapter


def make_adapter(chat_reply, chat_status=200, seen=None):
    seen = seen if seen is not None else []

    def handler(request):
        seen.append((request.method, request.url.path))
        if request.method == "POST" and request.url.path == "/conversations":
            return httpx.Response(200, json={"id": "c1", "title": "New chat"})
        if request.method == "POST" and request.url.path == "/chat":
            body = json.loads(request.content)
            assert body == {"message": "hi", "conversation": "c1"}
            return httpx.Response(chat_status, text=chat_reply)
        if request.method == "DELETE":
            return httpx.Response(200, json={"ok": True})
        return httpx.Response(404)

    client = httpx.Client(transport=httpx.MockTransport(handler), base_url="http://nova.test")
    return NovaAdapter(client=client, retry_wait_s=0)


def test_plain_answer_uses_a_fresh_conversation_and_cleans_up():
    seen = []
    out = make_adapter("Hello!", seen=seen).run("hi")
    assert out.answer == "Hello!"
    assert out.error is None
    assert seen == [
        ("POST", "/conversations"),
        ("POST", "/chat"),
        ("DELETE", "/conversations/c1"),
    ]


def test_token_trailer_is_not_part_of_the_answer():
    reply = "Hello!\x00" + json.dumps({"prompt": 1, "reply": 2, "total": 3})
    assert make_adapter(reply).run("hi").answer == "Hello!"


def test_tools_in_trailer_become_tools_used():
    reply = "42\x00" + json.dumps({"total": 3, "tools": ["calculator"]})
    assert make_adapter(reply).run("hi").tools_used == ["calculator"]


def test_http_error_is_recorded():
    out = make_adapter('{"error": "Password required"}', chat_status=401).run("hi")
    assert "401" in out.error
    assert "Password required" in out.error


def test_error_line_inside_the_stream_is_recorded():
    reply = "Part\n[Nova couldn't reply: error 503. Try again in a moment.]"
    out = make_adapter(reply).run("hi")
    assert out.answer == "Part"
    assert "couldn't reply" in out.error


def test_timeout_is_recorded():
    def handler(request):
        raise httpx.ReadTimeout("slow", request=request)

    client = httpx.Client(transport=httpx.MockTransport(handler), base_url="http://nova.test")
    out = NovaAdapter(client=client, retry_wait_s=0).run("hi")
    assert "timeout" in out.error


def test_missing_password_is_an_error(monkeypatch):
    monkeypatch.delenv("NOVA_PASSWORD", raising=False)
    with pytest.raises(ValueError):
        NovaAdapter()