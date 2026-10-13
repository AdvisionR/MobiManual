"""The triage conversation against a scripted model."""

import pytest
from fakes import FakeLLM
from fakes import submit as submit_tool

from docbot.drafting.manual import Manual
from docbot.drafting.triage import triage, validate
from docbot.llm import Turn

MANUAL = Manual({"_devices.md": "# Devices\n\n## Filters\n",
                 "_policies_kiosk.md": "# Kiosk Modes\n\nLeaving kiosk mode requires the\ndevice passcode.\n"})
MR = {"iid": 12, "title": "Give kiosk policies their own exit passcode", "description": "A new field."}
DIFFS = [{"old_path": "kiosk.controller.js", "new_path": "kiosk.controller.js", "diff": "@@ -1 +1 @@\n+exitPasscode\n"}]
WRONG = {"kind": "wrong", "page": "_policies_kiosk.md", "quote": "Leaving kiosk mode requires the device passcode.",
         "why": "It now requires the exit passcode."}


def submit(decision: str, reason: str = "kiosk policies gain a passcode", evidence=(), id: str = "t1") -> Turn:
    return submit_tool("submit_triage", {"decision": decision, "reason": reason, "evidence": list(evidence)}, id)


def test_a_valid_answer_comes_back():
    llm = FakeLLM(submit("doc-impact", evidence=[WRONG]))
    result = triage(llm, MR, DIFFS, MANUAL, edited=["_devices.md"], sha="a" * 40)
    assert result["outcome"] == "submitted"
    assert result["answer"] == {"decision": "doc-impact", "reason": "kiosk policies gain a passcode",
                                "evidence": [WRONG]}
    (opened,) = llm.opened
    assert opened["tools"] == ["submit_triage"]
    assert opened["cache_key"] == "docbot-aaaaaaaaaaaa-triage"
    assert result["system"] == opened["system"]
    assert result["task"] == opened["task"]


def test_the_task_holds_the_whole_manual_then_the_change():
    llm = FakeLLM(submit("no-doc-impact"))
    triage(llm, MR, DIFFS, MANUAL, edited=["_devices.md"], sha="a" * 40)
    task = llm.opened[0]["task"]
    assert "## Page _devices.md (already edited in this merge request)" in task
    assert "## Page _policies_kiosk.md\n\n````markdown\n# Kiosk Modes\n\nLeaving kiosk mode requires the\n" in task
    assert "# Merge request !12: Give kiosk policies their own exit passcode" in task
    assert "A new field." in task
    assert "+exitPasscode" in task
    assert task.index("## Page _policies_kiosk.md") < task.index("# Merge request !12")


def test_the_system_prompt_names_the_product_and_how_a_flag_counts():
    llm = FakeLLM(submit("no-doc-impact"))
    triage(llm, MR, DIFFS, MANUAL, edited=[], sha="a" * 40, product="Zulip, a team chat application")
    system = llm.opened[0]["system"]
    assert "user manual of Zulip, a team chat application true to" in system
    assert "switches a feature flag on makes what the flag hid usable" in system


def test_an_invalid_answer_goes_back_to_the_model_which_fixes_it():
    unknown = {**WRONG, "page": "Kiosk Modes"}
    llm = FakeLLM(submit("doc-impact", evidence=[unknown]), submit("doc-impact", evidence=[WRONG], id="t2"))
    result = triage(llm, MR, DIFFS, MANUAL, edited=[], sha="a" * 40)
    assert result["outcome"] == "submitted"
    (rejected,), = llm.sent
    assert rejected.text == "not accepted: evidence 1: no page 'Kiosk Modes' in the table of contents"


@pytest.mark.parametrize("answer, problem", [
    ({"decision": "maybe", "reason": "x"}, "decision must be one of"),
    ({"decision": "doc-impact"}, "'reason' must say why"),
    ({"decision": "doc-impact", "reason": "  "}, "'reason' must say why"),
    ({"decision": "doc-impact", "reason": "x", "evidence": "the kiosk page"}, "'evidence' must be a list"),
    ({"decision": "doc-impact", "reason": "x", "evidence": [{**WRONG, "kind": "stale"}]}, "kind must be one of"),
    ({"decision": "doc-impact", "reason": "x", "evidence": [{"kind": "missing", "why": "x"}]}, "needs 'page' and 'quote'"),
    ({"decision": "doc-impact", "reason": "x", "evidence": [{**WRONG, "page": "_policie_kiosk.md"}]},
     "did you mean _policies_kiosk.md"),
    ({"decision": "doc-impact", "reason": "x", "evidence": [{**WRONG, "quote": "kiosk"}]}, "at least a phrase"),
    ({"decision": "doc-impact", "reason": "x", "evidence": [{**WRONG, "quote": "Leaving kiosk mode needs a PIN."}]},
     "_policies_kiosk.md does not contain"),
])
def test_validation_names_the_problem(answer, problem):
    assert problem in validate(answer, MANUAL)


@pytest.mark.parametrize("answer", [
    {"decision": "no-doc-impact", "reason": "a refactor"},
    {"decision": "no-doc-impact", "reason": "a refactor", "evidence": []},
    # A quote matches across line breaks and spacing.
    {"decision": "doc-impact", "reason": "x", "evidence": [
        {**WRONG, "quote": "Leaving kiosk mode   requires the device\npasscode."}]},
    # Whether the evidence is right is the model's call: a label is not checked against the
    # diff, and doc-impact without evidence still counts.
    {"decision": "doc-impact", "reason": "x", "evidence": [
        {"kind": "missing", "page": "_policies_kiosk.md", "quote": "# Kiosk Modes", "label": "Exit code", "why": "x"}]},
    {"decision": "doc-impact", "reason": "x", "evidence": []},
    {"decision": "doc-impact", "reason": "x", "evidence": [{"kind": "new-page", "label": "Locations", "why": "x"}]},
])
def test_valid_answers(answer):
    assert validate(answer, MANUAL) is None
