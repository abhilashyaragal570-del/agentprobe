import time

import httpx

from ..schemas import AgentOutput

RETRY_PREFIXES = ("HTTP 429", "HTTP 503")


class HttpAdapter:
    """Call any HTTP endpoint that takes JSON in and returns JSON out.

    The input goes into the request body under `request_field`. The answer is
    read from the JSON reply at `answer_field`, and the names of the tools used
    (optional) from `tools_field`. Both are dotted paths such as "data.reply"
    or "choices.0.text".
    """

    def __init__(
        self,
        url: str,
        request_field: str = "message",
        answer_field: str = "answer",
        tools_field: str | None = None,
        headers: dict[str, str] | None = None,
        extra_body: dict | None = None,
        timeout_s: float = 60.0,
        client: httpx.Client | None = None,
        max_retries: int = 3,
        retry_wait_s: float = 10.0,
    ):
        if not url:
            raise ValueError("url is required")
        self.url = url
        self.request_field = request_field
        self.answer_field = answer_field
        self.tools_field = tools_field
        self.headers = dict(headers or {})
        self.extra_body = dict(extra_body or {})
        self.max_retries = max_retries
        self.retry_wait_s = retry_wait_s
        self._client = client if client is not None else httpx.Client(timeout=timeout_s)

    def run(self, input_text: str) -> AgentOutput:
        output = self._run_once(input_text)
        for attempt in range(self.max_retries):
            if not _is_retryable(output):
                break
            # Rate limits clear with time: wait longer on each retry.
            time.sleep(self.retry_wait_s * (attempt + 1))
            output = self._run_once(input_text)
        return output

    def _run_once(self, input_text: str) -> AgentOutput:
        body = dict(self.extra_body)
        body[self.request_field] = input_text
        try:
            response = self._client.post(self.url, json=body, headers=self.headers)
        except httpx.TimeoutException:
            return AgentOutput(error="timeout talking to the agent")
        except httpx.HTTPError as error:
            return AgentOutput(error=f"{type(error).__name__}: {error}")

        if response.status_code >= 400:
            return AgentOutput(
                error=f"HTTP {response.status_code}: {response.text[:200]}"
            )
        try:
            data = response.json()
        except ValueError:
            return AgentOutput(error=f"reply was not JSON: {response.text[:200]}")

        found, value = _dig(data, self.answer_field)
        if not found:
            return AgentOutput(
                error=f"answer field {self.answer_field!r} not found in the reply"
            )
        answer = "" if value is None else str(value)

        tools: list[str] = []
        if self.tools_field:
            found_tools, raw = _dig(data, self.tools_field)
            if found_tools:
                tools = _tool_names(raw)
        return AgentOutput(answer=answer.strip(), tools_used=tools)


def _is_retryable(output: AgentOutput) -> bool:
    return bool(output.error) and output.error.startswith(RETRY_PREFIXES)


def _dig(data, path: str):
    """Follow a dotted path through dicts and lists. Returns (found, value)."""
    current = data
    for part in path.split("."):
        if isinstance(current, dict) and part in current:
            current = current[part]
        elif isinstance(current, list) and part.isdigit() and int(part) < len(current):
            current = current[int(part)]
        else:
            return False, None
    return True, current


def _tool_names(raw) -> list[str]:
    if not isinstance(raw, list):
        return []
    names: list[str] = []
    for item in raw:
        if isinstance(item, str):
            names.append(item)
        elif isinstance(item, dict) and isinstance(item.get("name"), str):
            names.append(item["name"])
    return names