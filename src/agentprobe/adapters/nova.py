import json
import os

import httpx

from ..schemas import AgentOutput

TOKEN_MARKER = "\x00"
STREAM_ERROR_MARKER = "[Nova couldn't reply"


class NovaAdapter:
    """Call a running Nova server over HTTP and turn its reply into an AgentOutput."""

    def __init__(
        self,
        base_url: str = "http://127.0.0.1:8000",
        password: str | None = None,
        timeout_s: float = 60.0,
        client: httpx.Client | None = None,
    ):
        if client is None:
            password = password or os.environ.get("NOVA_PASSWORD")
            if not password:
                raise ValueError("Set the NOVA_PASSWORD environment variable or pass password=")
            client = httpx.Client(
                base_url=base_url, auth=("agentprobe", password), timeout=timeout_s
            )
        self._client = client

    def run(self, input_text: str) -> AgentOutput:
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
