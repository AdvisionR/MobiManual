"""The drafting conversation against a scripted model."""

import pytest

from docbot.drafting.proposal import propose, validate
from docbot.llm import Tool, ToolCall, ToolResult, Turn

PAGES = {"_policies_kiosk.md": "# Kiosk Modes\n\nLeaving kiosk mode requires the device passcode.\n",
         "_devices.md": "# Devices\n\nThe device list.\n"}
MR = {"iid": 12, "title": "Give kiosk policies their own exit passcode", "description": "A new field."}
DIFFS = [{"old_path": "kiosk.controller.js", "new_path": "kiosk.controller.js", "diff": "@@ -1 +1 @@\n+exitPasscode\n"}]
USAGE = {"input_tokens": 10, "cached_tokens": 0, "output_tokens": 5}

EDIT = {"page": "_policies_kiosk.md", "decision": "edit", "reason": "new passcode",
        "edits": [{"find": "requires the device passcode.", "replace": "requires the policy's exit passcode."}]}
UNCHANGED = {"page": "_devices.md", "decision": "no-change", "reason": "not affected"}


def submit(*pages: dict, id: str = "s1") -> Turn:
    return Turn([ToolCall(id, "submit_proposal", {"pages": list(pages), "uncertainties": []})], "", False, USAGE)


class FakeLLM:
    name = "fake/model"

    def __init__(self, *turns: Turn):
        self.turns = list(turns)
        self.opened: dict = {}
        self.sent: list[list[ToolResult]] = []

    def conversation(self, system: str, task: str, tools: list[Tool], cache_key: str):
        self.opened = {"system": system, "task": task, "tools": [t.name for t in tools], "cache_key": cache_key}
        return self

    def step(self) -> Turn:
        return self.turns.pop(0)

    def add_results(self, results: list[ToolResult]) -> None:
        self.sent.append(results)


def test_a_valid_proposal_comes_back_with_the_edited_pages():
    llm = FakeLLM(submit(EDIT, UNCHANGED))
    result = propose(llm, MR, DIFFS, PAGES, sha="a" * 40)
    assert result["outcome"] == "submitted"
    assert result["context"] == "diff"
    assert result["edited"] == {"_policies_kiosk.md": "# Kiosk Modes\n\nLeaving kiosk mode requires the policy's exit passcode.\n"}
    assert llm.opened["tools"] == ["submit_proposal"]
    assert llm.opened["cache_key"] == "docbot-aaaaaaaaaaaa-draft"
    assert "Leaving kiosk mode requires the device passcode." in llm.opened["task"]
    assert "+exitPasscode" in llm.opened["task"]


def test_a_broken_edit_goes_back_to_the_model_which_fixes_it():
    broken = {**EDIT, "edits": [{"find": "requires the passcode.", "replace": "x"}]}
    llm = FakeLLM(submit(broken, UNCHANGED), submit(EDIT, UNCHANGED, id="s2"))
    result = propose(llm, MR, DIFFS, PAGES, sha="a" * 40)
    assert result["outcome"] == "submitted"
    (rejected,), = llm.sent
    assert "_policies_kiosk.md: edit 1: 'find' does not occur in the page" in rejected.text


@pytest.mark.parametrize("pages, problem", [
    ([EDIT], "no answer for _devices.md"),
    ([EDIT, UNCHANGED, UNCHANGED], "_devices.md is answered more than once"),
    ([EDIT, {**UNCHANGED, "page": "_users.md"}], "'_users.md' is not one of the pages given"),
    ([{**EDIT, "edits": []}, UNCHANGED], "decision 'edit' needs at least one edit"),
    ([EDIT, {**UNCHANGED, "edits": EDIT["edits"]}], "only decision 'edit' may carry edits"),
    ([EDIT, {**UNCHANGED, "decision": "maybe"}], "decision must be one of"),
    ([EDIT, {**UNCHANGED, "page": ["_devices.md"]}], "is not one of the pages given"),
])
def test_validation_names_the_problem(pages, problem):
    assert problem in validate({"pages": pages, "uncertainties": []}, PAGES)
