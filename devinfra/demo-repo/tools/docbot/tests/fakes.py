"""A scripted model, for the tests of the steps that talk to one."""

from docbot.llm import Tool, ToolCall, ToolResult, Turn

USAGE = {"input_tokens": 10, "cached_tokens": 0, "output_tokens": 5}


def submit(tool: str, arguments: dict, id: str = "s1") -> Turn:
    return Turn([ToolCall(id, tool, arguments)], "", False, USAGE)


class FakeLLM:
    """Replays scripted turns across every conversation it opens, in order, and records what DocBot sends."""

    name = "fake/model"

    def __init__(self, *turns: Turn):
        self.turns = list(turns)
        self.opened: list[dict] = []
        self.sent: list[list[ToolResult]] = []

    def conversation(self, system: str, task: str, tools: list[Tool], cache_key: str):
        self.opened.append({"system": system, "task": task, "tools": [t.name for t in tools], "cache_key": cache_key})
        return self

    def step(self) -> Turn:
        return self.turns.pop(0)

    def add_results(self, results: list[ToolResult]) -> None:
        self.sent.append(results)
