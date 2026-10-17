import json

import httpx
import pytest

from agentprobe.adapters.http import HttpAdapter

URL = "http://agent.test/ask"


def adapter(handler, **kwargs):
    client = httpx.Client(transport=httpx.MockTransport(handler))
    kwargs.setdefault("retry_wait_s", 0)
    return HttpAdapter(URL, client=client, **kwargs)


def ok(payload):
    return lambda request: httpx.Response(200, json=payload)


def test_sends_input_under_request_field_and_reads_answer():
    seen = {}

    def handler(request):
        seen["body"] = json.loads(request.content)
        seen["url"] = str(request.url)
        return httpx.Response(200, json={"answer": " 42 "})

    out = adapter(handler).run("what is 6 * 7?")
    assert seen["url"] == URL
    assert seen["body"] == {"message": "what is 6 * 7?"}
    assert out.answer == "42"
    assert out.error is None


def test_custom_request_and_answer_fields():
    seen = {}

    def handler(request):
        seen["body"] = json.loads(request.content)
        return httpx.Response(200, json={"reply": "hi"})

    out = adapter(handler, request_field="q", answer_field="reply").run("hello")
    assert seen["body"] == {"q": "hello"}
    assert out.answer == "hi"


def test_nested_answer_path():
    out = adapter(ok({"data": {"reply": "deep"}}), answer_field="data.reply").run("x")
    assert out.answer == "deep"


def test_list_index_in_path():
    payload = {"choices": [{"text": "first"}, {"text": "second"}]}
    out = adapter(ok(payload), answer_field="choices.1.text").run("x")
    assert out.answer == "second"


def test_tools_read_from_field():
    payload = {"answer": "ok", "tools": ["calculator", "list_files"]}
    out = adapter(ok(payload), tools_field="tools").run("x")
    assert out.tools_used == ["calculator", "list_files"]


def test_tools_from_dicts_with_name():
    payload = {"answer": "ok", "calls": [{"name": "search"}, {"id": 1}]}
    out = adapter(ok(payload), tools_field="calls").run("x")
    assert out.tools_used == ["search"]


def test_no_tools_field_gives_empty_tools():
    out = adapter(ok({"answer": "ok", "tools": ["a"]})).run("x")
    assert out.tools_used == []


def test_missing_tools_field_gives_empty_tools_not_error():
    out = adapter(ok({"answer": "ok"}), tools_field="tools").run("x")
    assert out.tools_used == []
    assert out.error is None


def test_missing_answer_field_is_error():
    out = adapter(ok({"other": "x"})).run("x")
    assert out.error is not None
    assert "'answer'" in out.error


def test_number_answer_is_converted_to_string():
    out = adapter(ok({"answer": 422734})).run("x")
    assert out.answer == "422734"


def test_null_answer_is_empty_string():
    out = adapter(ok({"answer": None})).run("x")
    assert out.answer == ""
    assert out.error is None


def test_http_error_is_error_with_status():
    out = adapter(lambda r: httpx.Response(401, text="nope")).run("x")
    assert out.error == "HTTP 401: nope"


def test_non_json_reply_is_error():
    out = adapter(lambda r: httpx.Response(200, text="not json")).run("x")
    assert out.error is not None
    assert "not JSON" in out.error


def test_timeout_is_error():
    def handler(request):
        raise httpx.ReadTimeout("slow", request=request)

    out = adapter(handler).run("x")
    assert out.error == "timeout talking to the agent"


def test_extra_body_and_headers_are_sent():
    seen = {}

    def handler(request):
        seen["body"] = json.loads(request.content)
        seen["auth"] = request.headers.get("authorization")
        return httpx.Response(200, json={"answer": "ok"})

    adapter(
        handler,
        extra_body={"model": "m1"},
        headers={"Authorization": "Bearer secret"},
    ).run("hi")
    assert seen["body"] == {"model": "m1", "message": "hi"}
    assert seen["auth"] == "Bearer secret"


def test_retries_429_then_succeeds():
    calls = {"n": 0}

    def handler(request):
        calls["n"] += 1
        if calls["n"] < 3:
            return httpx.Response(429, text="slow down")
        return httpx.Response(200, json={"answer": "done"})

    out = adapter(handler).run("x")
    assert calls["n"] == 3
    assert out.answer == "done"
    assert out.error is None


def test_gives_up_after_max_retries():
    calls = {"n": 0}

    def handler(request):
        calls["n"] += 1
        return httpx.Response(503, text="down")

    out = adapter(handler, max_retries=2).run("x")
    assert calls["n"] == 3
    assert out.error.startswith("HTTP 503")


def test_does_not_retry_other_errors():
    calls = {"n": 0}

    def handler(request):
        calls["n"] += 1
        return httpx.Response(400, text="bad")

    adapter(handler).run("x")
    assert calls["n"] == 1


def test_empty_url_raises():
    with pytest.raises(ValueError):
        HttpAdapter("")