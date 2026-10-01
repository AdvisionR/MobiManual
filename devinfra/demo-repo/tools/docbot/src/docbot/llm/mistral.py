"""Mistral, through its Python SDK. The only module that imports mistralai.

Every step sets tool_choice "any", so the model calls a tool on every turn and a
conversation can only end through one of DocBot's submit tools. Prompt caching
is requested with a key that stays the same for the whole conversation. Mistral
does not guarantee a hit; usage reports the cached tokens either way.
"""

import json

import httpx2
from mistralai.client import Mistral
from mistralai.client.errors import MistralError, NoResponseError
from mistralai.client.models import TextChunk, ToolTypedDict

from docbot.llm import LLMError, Tool, ToolCall, ToolResult, Turn

TIMEOUT_MS = 120_000


class MistralLLM:
    def __init__(self, api_key: str, model: str, client: Mistral | None = None):
        self._client = client or Mistral(api_key=api_key, timeout_ms=TIMEOUT_MS)
        self._model = model
        self.name = f"mistral/{model}"

    def conversation(self, system: str, task: str, tools: list[Tool], cache_key: str) -> "MistralConversation":
        return MistralConversation(self._client, self._model, system, task, tools, cache_key)


class MistralConversation:
    def __init__(self, client: Mistral, model: str, system: str, task: str, tools: list[Tool], cache_key: str):
        self._client, self._model, self._cache_key = client, model, cache_key
        self._tools: list[ToolTypedDict] = [
            {"type": "function", "function": {"name": t.name, "description": t.description, "parameters": t.schema}}
            for t in tools]
        self._messages: list = [{"role": "system", "content": system}, {"role": "user", "content": task}]

    def step(self) -> Turn:
        try:
            response = self._client.chat.complete(
                model=self._model, messages=self._messages, tools=self._tools,
                tool_choice="any", prompt_cache_key=self._cache_key)
        except (MistralError, NoResponseError, httpx2.TransportError) as e:
            raise LLMError(f"mistral: {e}") from e
        choice = response.choices[0]
        message = choice.message
        if message is None:
            raise LLMError("mistral: a response without a message")
        # Sent back unchanged: the next request must repeat this turn exactly.
        self._messages.append(message)
        calls = [ToolCall(c.id or "", c.function.name, _arguments(c.function.arguments))
                 for c in message.tool_calls or []]
        return Turn(calls, _text(message.content), choice.finish_reason in ("length", "model_length"),
                    _usage(response.usage))

    def add_results(self, results: list[ToolResult]) -> None:
        for r in results:
            # Mistral's tool message has no error flag, so the text carries it.
            content = f"Error: {r.text}" if r.is_error else r.text
            self._messages.append({"role": "tool", "tool_call_id": r.id, "name": r.name, "content": content})


def _arguments(raw: dict | str) -> dict | None:
    if isinstance(raw, dict):
        return raw
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError:
        return None
    return parsed if isinstance(parsed, dict) else None


def _text(content) -> str:
    """The message's text. Reasoning models may send a list of chunks, thinking included."""
    if content is None or isinstance(content, str):
        return content or ""
    return "".join(chunk.text for chunk in content if isinstance(chunk, TextChunk))


def _usage(usage) -> dict:
    # cached_tokens is not a typed field of the SDK's UsageInfo; it arrives as an extra.
    details = (usage.model_extra or {}).get("prompt_tokens_details") or {}
    return {"input_tokens": usage.prompt_tokens or 0,
            "cached_tokens": details.get("cached_tokens") or 0,
            "output_tokens": usage.completion_tokens or 0}
