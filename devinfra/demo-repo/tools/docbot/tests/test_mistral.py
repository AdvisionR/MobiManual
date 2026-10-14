"""The Mistral adapter's translation, against a stand-in client that returns SDK response models."""

import httpx2
import pytest
from mistralai.client.models import ChatCompletionResponse
from mistralai.client.types import UNSET

from docbot.llm import LLMError, Tool, ToolResult
from docbot.llm.mistral import RETRIES, MistralLLM

GREP = Tool("grep", "Search.", {"type": "object", "properties": {"pattern": {"type": "string"}}})
SUBMIT = Tool("submit", "Submit.", {"type": "object", "properties": {}})


def response(tool_calls=(), content="", finish_reason="tool_calls", cached=None) -> ChatCompletionResponse:
    usage: dict = {"prompt_tokens": 1000, "completion_tokens": 50, "total_tokens": 1050}
    if cached is not None:
        usage["prompt_tokens_details"] = {"cached_tokens": cached}
    return ChatCompletionResponse.model_validate({
        "id": "r", "object": "chat.completion", "model": "mistral-medium-3-5", "created": 1, "usage": usage,
        "choices": [{"index": 0, "finish_reason": finish_reason,
                     "message": {"role": "assistant", "content": content, "tool_calls": list(tool_calls)}}]})


def tool_call(id: str, name: str, arguments) -> dict:
    return {"id": id, "type": "function", "function": {"name": name, "arguments": arguments}}


class FakeClient:
    """Stands in for mistralai's Mistral: records each chat.complete request."""

    def __init__(self, *responses):
        self.responses, self.requests = list(responses), []
        self.chat = self

    def complete(self, **request):
        self.requests.append({**request, "messages": list(request["messages"])})
        answer = self.responses.pop(0)
        if isinstance(answer, Exception):
            raise answer
        return answer


def conversation(client, tools=(GREP, SUBMIT), reasoning_effort=None):
    return MistralLLM("key", "mistral-medium-3-5", client=client, reasoning_effort=reasoning_effort).conversation(
        "system text", "task text", list(tools), cache_key="docbot-abc-draft")


def test_a_tool_added_later_is_sent_from_the_next_request_on():
    client = FakeClient(response([tool_call("a1", "submit", "{}")]), response([tool_call("a2", "grep", "{}")]))
    chat = conversation(client, tools=[SUBMIT])
    chat.step()
    chat.add_tools([GREP])
    chat.add_results([ToolResult("a1", "submit", "accepted")])
    chat.step()
    first, second = client.requests
    assert [t["function"]["name"] for t in first["tools"]] == ["submit"]
    assert first["tool_choice"] == {"type": "function", "function": {"name": "submit"}}
    assert [t["function"]["name"] for t in second["tools"]] == ["submit", "grep"]
    assert second["tool_choice"] == "any"


def test_a_request_carries_tools_forced_tool_use_and_the_cache_key():
    client = FakeClient(response([tool_call("a1", "grep", '{"pattern": "kiosk"}')]))
    turn = conversation(client).step()
    request = client.requests[0]
    assert request["model"] == "mistral-medium-3-5"
    assert request["tool_choice"] == "any"
    assert request["prompt_cache_key"] == "docbot-abc-draft"
    assert request["tools"][0] == {"type": "function", "function": {
        "name": "grep", "description": "Search.", "parameters": GREP.schema}}
    assert request["messages"] == [{"role": "system", "content": "system text"},
                                   {"role": "user", "content": "task text"}]
    assert [(c.id, c.name, c.arguments) for c in turn.calls] == [("a1", "grep", {"pattern": "kiosk"})]


def test_the_reasoning_effort_is_sent_on_every_request_when_given():
    client = FakeClient(response([tool_call("a1", "grep", {})]), response([tool_call("a2", "grep", {})]))
    chat = conversation(client, reasoning_effort="high")
    chat.step()
    chat.add_results([ToolResult("a1", "grep", "no match")])
    chat.step()
    assert [r["reasoning_effort"] for r in client.requests] == ["high", "high"]


def test_without_a_reasoning_effort_the_field_is_left_out():
    client = FakeClient(response([tool_call("a1", "grep", {})]))
    conversation(client).step()
    assert client.requests[0]["reasoning_effort"] is UNSET


def test_a_lone_tool_is_named_in_tool_choice():
    client = FakeClient(response([tool_call("a1", "submit", {})]))
    conversation(client, tools=[SUBMIT]).step()
    assert client.requests[0]["tool_choice"] == {"type": "function", "function": {"name": "submit"}}


def test_the_client_retries_rate_limits_and_server_errors():
    llm = MistralLLM("key", "mistral-medium-3-5")
    config = llm._client.sdk_configuration
    assert config.retry_config is RETRIES
    assert config.timeout_ms == 300_000


def test_the_next_request_repeats_the_whole_conversation_with_the_results():
    client = FakeClient(response([tool_call("a1", "grep", {"pattern": "kiosk"})]), response(content="done"))
    chat = conversation(client)
    chat.step()
    chat.add_results([ToolResult("a1", "grep", "no matches", is_error=True)])
    chat.step()
    *_, assistant, tool = client.requests[1]["messages"]
    assert assistant.tool_calls[0].id == "a1"  # the model's own turn, sent back as it came
    assert tool == {"role": "tool", "tool_call_id": "a1", "name": "grep", "content": "Error: no matches"}


def test_arguments_that_are_not_a_json_object_become_none():
    client = FakeClient(response([tool_call("a1", "grep", "{not json"), tool_call("a2", "grep", "[1]")]))
    assert [c.arguments for c in conversation(client).step().calls] == [None, None]


def test_usage_includes_cached_tokens_and_length_means_cut_off():
    turn = conversation(FakeClient(response(finish_reason="length", cached=640))).step()
    assert turn.cut_off
    assert turn.usage == {"input_tokens": 1000, "cached_tokens": 640, "output_tokens": 50}
    assert conversation(FakeClient(response())).step().usage["cached_tokens"] == 0


def test_an_unreachable_provider_is_an_llm_error():
    with pytest.raises(LLMError, match="mistral: refused"):
        conversation(FakeClient(httpx2.ConnectError("refused"))).step()
