"""The tool loop against a scripted conversation: no model, no network."""

from docbot.llm import ToolCall, ToolResult, Turn, agent
from docbot.llm.agent import ToolError

USAGE = {"input_tokens": 10, "cached_tokens": 0, "output_tokens": 5}


def turn(*calls: ToolCall, cut_off=False) -> Turn:
    return Turn(list(calls), "", cut_off, USAGE)


def call(name: str, arguments: dict | None = None, id: str = "c1") -> ToolCall:
    return ToolCall(id, name, {} if arguments is None else arguments)


class FakeConversation:
    """Replays scripted turns and records what DocBot sends back."""

    def __init__(self, *turns: Turn):
        self.turns = list(turns)
        self.sent: list[list[ToolResult]] = []

    def step(self) -> Turn:
        return self.turns.pop(0)

    def add_results(self, results: list[ToolResult]) -> None:
        self.sent.append(results)


def accept_ok(submission: dict) -> str | None:
    return None if submission.get("ok") else "ok must be true"


def lookup(arguments: dict) -> str:
    if arguments.get("key") == "missing":
        raise ToolError("no such key")
    return f"value of {arguments['key']}"


HANDLERS = {"lookup": lookup}


def run(conversation, max_calls=agent.MAX_CALLS):
    return agent.run(conversation, HANDLERS, "submit", accept_ok, max_calls=max_calls)


def test_a_tool_result_goes_back_and_a_valid_submission_ends_the_loop():
    conversation = FakeConversation(turn(call("lookup", {"key": "a"})), turn(call("submit", {"ok": True})))
    result = run(conversation)
    assert result["outcome"] == "submitted"
    assert result["submission"] == {"ok": True}
    assert conversation.sent == [[ToolResult("c1", "lookup", "value of a")]]
    assert [c["name"] for t in result["turns"] for c in t["calls"]] == ["lookup", "submit"]


def test_a_rejected_submission_goes_back_as_an_error_and_can_be_corrected():
    conversation = FakeConversation(turn(call("submit", {"ok": False})), turn(call("submit", {"ok": True})))
    result = run(conversation)
    assert result["outcome"] == "submitted"
    (rejected,), = conversation.sent
    assert rejected.is_error
    assert rejected.text == "not accepted: ok must be true"
    assert result["turns"][0]["calls"][0]["error"] == "not accepted: ok must be true"


def test_parallel_calls_are_answered_together():
    conversation = FakeConversation(
        turn(call("lookup", {"key": "a"}, id="c1"), call("lookup", {"key": "b"}, id="c2")),
        turn(call("submit", {"ok": True})))
    run(conversation)
    assert [r.text for r in conversation.sent[0]] == ["value of a", "value of b"]


def test_tool_errors_unknown_tools_and_bad_arguments_go_back_to_the_model():
    conversation = FakeConversation(
        turn(call("lookup", {"key": "missing"}, id="c1"), call("shell", {}, id="c2"),
             ToolCall("c3", "lookup", None)),
        turn(call("submit", {"ok": True})))
    assert run(conversation)["outcome"] == "submitted"
    assert [(r.is_error, r.text) for r in conversation.sent[0]] == [
        (True, "no such key"),
        (True, "no tool named 'shell'"),
        (True, "the arguments are not a JSON object"),
    ]


def test_the_call_budget_stops_the_loop():
    conversation = FakeConversation(*[turn(call("lookup", {"key": "a"})) for _ in range(3)])
    result = run(conversation, max_calls=2)
    assert result["outcome"] == "stopped"
    assert "within 2 tool calls" in result["reason"]
    assert len(result["turns"]) == 2


def test_a_cut_off_answer_or_one_without_calls_stops_the_loop():
    assert run(FakeConversation(turn(cut_off=True)))["reason"] == "the model's answer was cut off"
    assert run(FakeConversation(turn()))["reason"] == "the model answered without calling a tool"
