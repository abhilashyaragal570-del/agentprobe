import json
import os
import time

import httpx

from ..schemas import AgentOutput

TOKEN_MARKER = "\x00"
STREAM_ERROR_MARKER = "[Nova couldn't reply"
RETRY_CODES = ("error 429", "error 503")


class NovaAdapter:
    """Call a running Nova server over HTTP and turn its reply into an AgentOutput."""

    def __init__(
        self,
        base_url: str = "http://127.0.0.1:8000",
        password: str | None = None,
        timeout_s: float = 60.0,
        client: httpx.Client | None = None,
        max_retries: int = 3,
        retry_wait_s: float = 10.0,
    ):
        if client is None:
            password = password or os.environ.get("NOVA_PASSWORD")
            if not password:
                raise ValueError("Set the NOVA_PASSWORD environment variable or pass password=")
            client = httpx.Client(
                base_url=base_url, auth=("agentprobe", password), timeout=timeout_s
            )
        self._client = client
        self.max_retries = max_retries
        self.retry_wait_s = retry_wait_s

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
        conversation_id = None
        try:
            # A fresh conversation per case, so cases cannot influence each other.
            created = self._client.post("/conversations")
            if created.status_code >= 400:
                return AgentOutput(error=_http_error(created))
            conversation_id = created.json()["id"]

            response = self._client.post(
                "/chat", json={"message": input_text, "conversation": conversation_id}
            )
            if response.status_code >= 400:
                return AgentOutput(error=_http_error(response))
            return _parse_chat_text(response.text)
        except httpx.TimeoutException:
            return AgentOutput(error="timeout talking to Nova")
        except httpx.HTTPError as error:
            return AgentOutput(error=f"{type(error).__name__}: {error}")
        finally:
            if conversation_id is not None:
                self._delete_quietly(conversation_id)

    def _delete_quietly(self, conversation_id: str) -> None:
        try:
            self._client.delete(f"/conversations/{conversation_id}")
        except httpx.HTTPError:
            pass  # cleanup must never turn a result into a failure


def _is_retryable(output: AgentOutput) -> bool:
    return bool(output.error) and any(code in output.error for code in RETRY_CODES)


def _http_error(response: httpx.Response) -> str:
    detail = None
    try:
        data = response.json()
        if isinstance(data, dict):
            detail = data.get("error") or data.get("detail")
    except ValueError:
        pass
    return f"HTTP {response.status_code}: {detail or response.text[:200]}"


def _parse_chat_text(text: str) -> AgentOutput:
    body, _, trailer = text.partition(TOKEN_MARKER)

    tools: list[str] = []
    if trailer:
        try:
            tools = list(json.loads(trailer).get("tools", []))
        except (ValueError, AttributeError):
            pass

    answer, found, rest = body.partition(STREAM_ERROR_MARKER)
    error = (found + rest).strip() if found else None
    return AgentOutput(answer=answer.strip(), tools_used=tools, error=error)