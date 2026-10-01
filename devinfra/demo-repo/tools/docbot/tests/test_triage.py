"""The triage conversation against a scripted model."""

import pytest
from fakes import FakeLLM
from fakes import submit as submit_tool

from docbot.drafting.manual import Manual
from docbot.drafting.triage import triage, validate
from docbot.llm import Turn

MANUAL = Manual({"_devices.md": "# Devices\n\n## Filters\n", "_policies_kiosk.md": "# Kiosk Modes\n"})
MR = {"iid": 12, "title": "Give kiosk policies their own exit passcode", "description": "A new field."}
DIFFS = [{"old_path": "kiosk.controller.js", "new_path": "kiosk.controller.js", "diff": "@@ -1 +1 @@\n+exitPasscode\n"}]


def submit(decision: str, reason: str = "kiosk policies gain a passcode", id: str = "t1") -> Turn:
    return submit_tool("submit_triage", {"decision": decision, "reason": reason}, id)


def test_a_valid_answer_comes_back():
    llm = FakeLLM(submit("doc-impact"))
    result = triage(llm, MR, DIFFS, MANUAL, edited=["_devices.md"], sha="a" * 40)
    assert result["outcome"] == "submitted"
    assert result["answer"] == {"decision": "doc-impact", "reason": "kiosk policies gain a passcode"}
    (opened,) = llm.opened
    assert opened["tools"] == ["submit_triage"]
    assert opened["cache_key"] == "docbot-aaaaaaaaaaaa-triage"
    assert "+exitPasscode" in opened["task"]
    assert "    ## Filters" in opened["task"]
    assert "_devices.md (already edited in this merge request)" in opened["task"]
    assert "MobiVisor, a mobile device management console" in opened["system"]
    assert result["system"] == opened["system"]
    assert result["task"] == opened["task"]


def test_the_product_can_be_named():
    llm = FakeLLM(submit("no-doc-impact"))
    triage(llm, MR, DIFFS, MANUAL, edited=[], sha="a" * 40, product="Zulip, a team chat application")
    assert "user manual of Zulip, a team chat application true to" in llm.opened[0]["system"]


def test_an_invalid_answer_goes_back_to_the_model_which_fixes_it():
    llm = FakeLLM(submit("maybe"), submit("doc-impact", id="t2"))
    result = triage(llm, MR, DIFFS, MANUAL, edited=[], sha="a" * 40)
    assert result["outcome"] == "submitted"
    (rejected,), = llm.sent
    assert rejected.text == "not accepted: decision must be one of doc-impact, no-doc-impact"


@pytest.mark.parametrize("answer, problem", [
    ({"decision": "maybe", "reason": "x"}, "decision must be one of"),
    ({"decision": "doc-impact"}, "'reason' must say why"),
    ({"decision": "doc-impact", "reason": "  "}, "'reason' must say why"),
])
def test_validation_names_the_problem(answer, problem):
    assert problem in validate(answer)


def test_no_doc_impact_with_a_reason_is_valid():
    assert validate({"decision": "no-doc-impact", "reason": "a refactor"}) is None
