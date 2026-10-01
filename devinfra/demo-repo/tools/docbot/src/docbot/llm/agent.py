"""The tool loop: DocBot's side of a conversation with a model.

The model never runs anything. Each turn it asks for tool calls; this module
answers them, sends the results back, and repeats until the model calls the
submit tool with an answer that passes validation, or the call budget is spent.
A validation failure goes back as a tool error, so the model can correct itself
in the same conversation.
"""

from collections.abc import Callable

from docbot.llm import Conversation, ToolCall, ToolResult

MAX_CALLS = 20

Handler = Callable[[dict], str]


class ToolError(Exception):
    """A tool call that cannot be answered. The message goes back to the model."""


def run(conversation: Conversation, handlers: dict[str, Handler], submit: str,
        validate: Callable[[dict], str | None], max_calls: int = MAX_CALLS) -> dict:
    """Drive the conversation to a validated submission.

    Returns {"outcome": "submitted", "submission": ..., "turns": [...]} or
    {"outcome": "stopped", "reason": ..., "turns": [...]}.
    """
    turns: list[dict] = []
    calls_made = 0
    while True:
        if calls_made >= max_calls:
            return _stopped(f"no valid {submit} within {max_calls} tool calls", turns)
        turn = conversation.step()
        entry: dict = {"text": turn.text, "usage": turn.usage, "calls": []}
        turns.append(entry)
        if turn.cut_off:
            return _stopped("the model's answer was cut off", turns)
        if not turn.calls:
            return _stopped("the model answered without calling a tool", turns)

        results = []
        for call in turn.calls:
            calls_made += 1
            result, submission = _answer(call, handlers, submit, validate)
            entry["calls"].append({"name": call.name, "arguments": call.arguments, "result_chars": len(result.text),
                                   **({"error": result.text} if result.is_error else {})})
            if submission is not None:
                return {"outcome": "submitted", "submission": submission, "turns": turns}
            results.append(result)
        conversation.add_results(results)


def _answer(call: ToolCall, handlers: dict[str, Handler], submit: str,
            validate: Callable[[dict], str | None]) -> tuple[ToolResult, dict | None]:
    """The result to send back, and the submission if this call was a valid one."""
    def error(text: str) -> tuple[ToolResult, None]:
        return ToolResult(call.id, call.name, text, is_error=True), None

    if call.arguments is None:
        return error("the arguments are not a JSON object")
    if call.name == submit:
        problem = validate(call.arguments)
        if problem:
            return error(f"not accepted: {problem}")
        return ToolResult(call.id, call.name, "accepted"), call.arguments
    handler = handlers.get(call.name)
    if handler is None:
        return error(f"no tool named {call.name!r}")
    try:
        return ToolResult(call.id, call.name, handler(call.arguments)), None
    except ToolError as e:
        return error(str(e))


def _stopped(reason: str, turns: list[dict]) -> dict:
    return {"outcome": "stopped", "reason": reason, "turns": turns}
