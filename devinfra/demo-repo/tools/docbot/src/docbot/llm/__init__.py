"""The seam between DocBot and a model provider. No provider SDK is imported here.

A Conversation is one exchange with a model: DocBot's task, the model's tool
calls and DocBot's tool results, kept in whatever format the provider needs.
The API behind it keeps no state, so each step sends the whole conversation
again. DocBot only ever appends to it. agent.py drives the loop.
"""

from dataclasses import dataclass
from typing import Protocol


class LLMError(Exception):
    """The provider could not be reached, or refused a request."""


@dataclass(frozen=True)
class Tool:
    name: str
    description: str
    schema: dict  # JSON Schema of the arguments


@dataclass(frozen=True)
class ToolCall:
    id: str
    name: str
    arguments: dict | None  # None if the model's arguments are not a JSON object


@dataclass(frozen=True)
class ToolResult:
    id: str
    name: str
    text: str
    is_error: bool = False


@dataclass(frozen=True)
class Turn:
    calls: list[ToolCall]
    text: str  # anything the model said besides its calls
    cut_off: bool  # the answer hit a length limit
    usage: dict  # input_tokens, cached_tokens, output_tokens


class Conversation(Protocol):
    def step(self) -> Turn: ...

    def add_results(self, results: list[ToolResult]) -> None: ...


class LLM(Protocol):
    name: str  # provider/model, for the log and the docs merge request

    def conversation(self, system: str, task: str, tools: list[Tool], cache_key: str) -> Conversation: ...
