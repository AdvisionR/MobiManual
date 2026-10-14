"""Mistral, through its Python SDK. The only module that imports mistralai.

The model calls a tool on every turn, so a conversation can only end through
one of DocBot's submit tools. With several tools, tool_choice is "any". With
only one, that tool is named: under "any", Medium 3.5 often wrote a lone
submit call out as text as well, and the parser then put that text into the
call's name. Naming the tool stopped it (2026-10-01 experiment, in the Mistral
prototype doc).

Prompt caching is requested with a key that stays the same for the whole
conversation. Mistral does not guarantee a hit; usage reports the cached
tokens either way. The SDK retries 429 and 5xx answers with backoff.
"""

import json
from typing import cast

import httpx2
from mistralai.client import Mistral
from mistralai.client.errors import MistralError, NoResponseError
from mistralai.client.models import (
    ChatCompletionRequestToolChoiceTypedDict,
    ReasoningEffort,
    TextChunk,
    ToolTypedDict,
)
from mistralai.client.types import UNSET, OptionalNullable
from mistralai.client.utils import BackoffStrategy, RetryConfig

from docbot.llm import LLMError, Tool, ToolCall, ToolResult, Turn

# One Medium 3.5 call took over 120 s on 2026-10-01.
TIMEOUT_MS = 300_000
# Retries 429 and 5xx: 1 s, growing by half each time, up to 30 s apart and 5 minutes in all.
RETRIES = RetryConfig("backoff", BackoffStrategy(1_000, 30_000, 1.5, 300_000), retry_connection_errors=True)


class MistralLLM:
    """reasoning_effort is sent on every request when given. Unsent, each model reasons by its
    own default: Medium 3.5 does not, Large 4 does. Both accept only "high" and "none" (2026-10-13)."""

    def __init__(self, api_key: str, model: str, client: Mistral | None = None,
                 reasoning_effort: str | None = None):
        self._client = client or Mistral(api_key=api_key, timeout_ms=TIMEOUT_MS, retry_config=RETRIES)
        self._model, self._effort = model, reasoning_effort
        self.name = f"mistral/{model}"

    def conversation(self, system: str, task: str, tools: list[Tool], cache_key: str) -> "MistralConversation":
        return MistralConversation(self._client, self._model, system, task, tools, cache_key, self._effort)


class MistralConversation:
    def __init__(self, client: Mistral, model: str, system: str, task: str, tools: list[Tool], cache_key: str,
                 reasoning_effort: str | None = None):
        self._client, self._model, self._cache_key = client, model, cache_key
        # UNSET leaves the field out of the request. The API refuses a value the model does not take.
        self._effort: OptionalNullable[ReasoningEffort] = (
            cast(ReasoningEffort, reasoning_effort) if reasoning_effort else UNSET)
        self._tools: list[ToolTypedDict] = []
        self._tool_choice: ChatCompletionRequestToolChoiceTypedDict = "any"
        self.add_tools(tools)
        self._messages: list = [{"role": "system", "content": system}, {"role": "user", "content": task}]

    def step(self) -> Turn:
        try:
            response = self._client.chat.complete(
                model=self._model, messages=self._messages, tools=self._tools,
                tool_choice=self._tool_choice, prompt_cache_key=self._cache_key, reasoning_effort=self._effort)
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

    def add_tools(self, tools: list[Tool]) -> None:
        # A new list: a request already sent keeps the tools it was sent with.
        self._tools = [*self._tools, *(
            {"type": "function", "function": {"name": t.name, "description": t.description, "parameters": t.schema}}
            for t in tools)]
        self._tool_choice = (
            {"type": "function", "function": {"name": self._tools[0]["function"]["name"]}} if len(self._tools) == 1
            else "any")

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
