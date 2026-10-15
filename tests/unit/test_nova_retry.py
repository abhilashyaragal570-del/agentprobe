import httpx

from agentprobe.adapters.nova import NovaAdapter


def make(replies, max_retries=3):
    calls = {"chat": 0}

    def handler(request):
        if request.method == "POST" and request.url.path == "/conversations":
            return httpx.Response(200, json={"id": "c1", "title": "New chat"})
        if request.method == "POST" and request.url.path == "/chat":
            reply = replies[min(calls["chat"], len(replies) - 1)]
            calls["chat"] += 1
            return httpx.Response(200, text=reply)
        return httpx.Response(200, json={"ok": True})

    client = httpx.Client(transport=httpx.MockTransport(handler), base_url="http://nova.test")
    adapter = NovaAdapter(client=client, max_retries=max_retries, retry_wait_s=0)
    return adapter, calls


RATE_LIMITED = "\n[Nova couldn't reply: error 429. Try again in a moment.]"


def test_a_rate_limit_is_retried_and_then_succeeds():
    adapter, calls = make([RATE_LIMITED, RATE_LIMITED, "Hello!"])
    out = adapter.run("hi")
    assert out.answer == "Hello!"
    assert out.error is None
    assert calls["chat"] == 3


def test_retries_stop_after_the_limit():
    adapter, calls = make([RATE_LIMITED], max_retries=2)
    out = adapter.run("hi")
    assert "429" in out.error
    assert calls["chat"] == 3  # first try + 2 retries


def test_other_errors_are_not_retried():
    adapter, calls = make(["\n[Nova couldn't reply: error 400. Bad request.]"])
    out = adapter.run("hi")
    assert "400" in out.error
    assert calls["chat"] == 1