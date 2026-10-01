"""The drafting conversation against a scripted model."""

import pytest
from fakes import FakeLLM
from fakes import submit as submit_tool

from docbot.drafting.manual import Manual
from docbot.drafting.proposal import MAX_EDITED_PAGES, propose, validate
from docbot.llm import ToolCall, Turn

PAGES = {"_policies_kiosk.md": "# Kiosk Modes\n\nLeaving kiosk mode requires the device passcode.\n",
         "_devices.md": "# Devices\n\nThe device list.\n",
         "_users.md": "# Users\n"}
MANUAL = Manual(PAGES)
MR = {"iid": 12, "title": "Give kiosk policies their own exit passcode", "description": "A new field."}
DIFFS = [{"old_path": "kiosk.controller.js", "new_path": "kiosk.controller.js", "diff": "@@ -1 +1 @@\n+exitPasscode\n"}]

EDIT = {"page": "_policies_kiosk.md", "decision": "edit", "reason": "new passcode",
        "edits": [{"find": "requires the device passcode.", "replace": "requires the policy's exit passcode."}]}
UNCHANGED = {"page": "_devices.md", "decision": "no-change", "reason": "not affected"}
USAGE = {"input_tokens": 10, "cached_tokens": 0, "output_tokens": 5}


def submit(*pages: dict, id: str = "s1") -> Turn:
    return submit_tool("submit_proposal", {"pages": list(pages), "uncertainties": []}, id)


def read(page: str, id: str = "r1") -> Turn:
    return Turn([ToolCall(id, "read_page", {"page": page})], "", False, USAGE)


def test_the_model_reads_the_page_it_chose_then_edits_it():
    llm = FakeLLM(read("_policies_kiosk.md"), submit(EDIT))
    result = propose(llm, MR, DIFFS, MANUAL, edited=[], sha="a" * 40)
    assert result["outcome"] == "submitted"
    assert result["context"] == "diff"
    assert result["edited"] == {"_policies_kiosk.md": "# Kiosk Modes\n\nLeaving kiosk mode requires the policy's exit passcode.\n"}
    (opened,) = llm.opened
    assert opened["tools"] == ["read_page", "search_manual", "submit_proposal"]
    assert opened["cache_key"] == "docbot-aaaaaaaaaaaa-draft"
    assert "+exitPasscode" in opened["task"]
    assert "_policies_kiosk.md\n    # Kiosk Modes" in opened["task"]
    assert "Leaving kiosk mode requires the device passcode." not in opened["task"]  # only through read_page
    (page_text,), = llm.sent
    assert "Leaving kiosk mode requires the device passcode." in page_text.text
    assert result["system"] == opened["system"]
    assert result["task"] == opened["task"]
    assert result["turns"][0]["calls"][0]["result"] == page_text.text


def test_pages_the_model_left_alone_need_no_answer():
    result = propose(FakeLLM(submit(EDIT)), MR, DIFFS, MANUAL, edited=[], sha="a" * 40)
    assert [e["page"] for e in result["proposal"]["pages"]] == ["_policies_kiosk.md"]


def test_a_broken_edit_goes_back_to_the_model_which_fixes_it():
    broken = {**EDIT, "edits": [{"find": "requires the passcode.", "replace": "x"}]}
    llm = FakeLLM(submit(broken, UNCHANGED), submit(EDIT, UNCHANGED, id="s2"))
    result = propose(llm, MR, DIFFS, MANUAL, edited=[], sha="a" * 40)
    assert result["outcome"] == "submitted"
    (rejected,), = llm.sent
    assert "_policies_kiosk.md: edit 1: 'find' does not occur in the page" in rejected.text


def test_repo_mode_adds_the_code_tools(tmp_path):
    class StubRepo:
        def tools(self):
            return [], {}

    llm = FakeLLM(submit(EDIT))
    result = propose(llm, MR, DIFFS, MANUAL, edited=[], sha="a" * 40, repo=StubRepo())  # type: ignore[arg-type]
    assert result["context"] == "repo"
    assert "search the code at the merge commit" in llm.opened[0]["task"]


def test_too_many_edited_pages_go_back_to_the_model():
    pages = {f"p{n}.md": f"text {n}\n" for n in range(MAX_EDITED_PAGES + 1)}
    entries = [{"page": p, "decision": "edit", "reason": "-", "edits": [{"find": "text", "replace": "new"}]}
               for p in pages]
    assert f"at most {MAX_EDITED_PAGES} pages may be edited" in (validate({"pages": entries, "uncertainties": []}, pages) or "")
    assert validate({"pages": entries[:MAX_EDITED_PAGES], "uncertainties": []}, pages) is None


@pytest.mark.parametrize("pages, problem", [
    ([], "'pages' must list at least one page"),
    ([EDIT, UNCHANGED, UNCHANGED], "_devices.md is answered more than once"),
    ([EDIT, {**UNCHANGED, "page": "_reports.md"}], "'_reports.md' is not a page in the table of contents"),
    ([{**EDIT, "edits": []}], "decision 'edit' needs at least one edit"),
    ([EDIT, {**UNCHANGED, "edits": EDIT["edits"]}], "only decision 'edit' may carry edits"),
    ([EDIT, {**UNCHANGED, "decision": "maybe"}], "decision must be one of"),
    ([{**UNCHANGED, "page": ["_devices.md"]}], "is not a page in the table of contents"),
])
def test_validation_names_the_problem(pages, problem):
    assert problem in (validate({"pages": pages, "uncertainties": []}, PAGES) or "")


def test_a_page_may_be_named_as_read_page_accepts_it():
    zulip = Manual({"docs/report-a-message.mdx": "Click **Submit**.\n"})
    entry = {"page": "report-a-message", "decision": "edit", "reason": "-",
             "edits": [{"find": "Click **Submit**.", "replace": "Click **Report**."}]}
    result = propose(FakeLLM(submit(entry)), MR, DIFFS, zulip, edited=[], sha="a" * 40)
    assert result["edited"] == {"docs/report-a-message.mdx": "Click **Report**.\n"}
