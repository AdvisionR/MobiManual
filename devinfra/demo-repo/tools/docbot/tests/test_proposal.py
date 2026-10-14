"""The drafting conversation against a scripted model."""

import pytest
from fakes import FakeLLM, FakeRepo
from fakes import submit as submit_tool

from docbot.drafting.manual import Manual
from docbot.drafting.proposal import (
    MAX_EDITED_PAGES,
    propose,
    validate,
    validate_new_pages,
)
from docbot.llm import ToolCall, Turn, agent

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
REPO = FakeRepo()


def submit(*pages: dict, missing=(), id: str = "s1") -> Turn:
    return submit_tool("submit_proposal", proposal(*pages, missing=missing), id)


def proposal(*pages: dict, missing=()) -> dict:
    return {"reason": "kiosk policies gain a passcode", "pages": list(pages), "missing_pages": list(missing),
            "uncertainties": []}


def write(*pages: dict, id: str = "w1") -> Turn:
    return submit_tool("submit_new_pages", {"pages": list(pages), "uncertainties": ["a screenshot of the map"]}, id)


LOCATIONS = {"page": "_locations.md", "describes": "the Locations page"}
NEW_PAGE = {"page": "_locations.md", "decision": "create", "after": "_devices", "reason": "a new screen",
            "text": "# Locations\n\nThe last position each device reported."}


def read(page: str, id: str = "r1") -> Turn:
    return Turn([ToolCall(id, "read_page", {"page": page})], "", False, USAGE)


def test_the_model_reads_the_page_it_chose_then_edits_it():
    llm = FakeLLM(read("_policies_kiosk.md"), submit(EDIT))
    result = propose(llm, MR, DIFFS, MANUAL, edited=[], sha="a" * 40, repo=REPO)
    assert result["outcome"] == "submitted"
    assert result["edited"] == {"_policies_kiosk.md": "# Kiosk Modes\n\nLeaving kiosk mode requires the policy's exit passcode.\n"}
    (opened,) = llm.opened
    assert opened["tools"] == ["read_page", "search_manual", "list_files", "grep", "read_file", "submit_proposal"]
    assert opened["cache_key"] == "docbot-aaaaaaaaaaaa-draft"
    assert "+exitPasscode" in opened["task"]
    assert "_policies_kiosk.md\n    # Kiosk Modes" in opened["task"]
    assert "Leaving kiosk mode requires the device passcode." not in opened["task"]  # only through read_page
    (page_text,), = llm.sent
    assert "Leaving kiosk mode requires the device passcode." in page_text.text
    assert result["system"] == opened["system"]
    assert result["task"] == opened["task"]
    assert result["turns"][0]["calls"][0]["result"] == page_text.text


def test_the_system_prompt_names_the_product_and_how_a_flag_counts():
    llm = FakeLLM(submit())
    propose(llm, MR, DIFFS, MANUAL, edited=[], sha="a" * 40, repo=REPO, product="Zulip, a team chat application")
    system = llm.opened[0]["system"]
    assert "user manual of Zulip, a team chat application true to" in system
    assert "switches a feature flag on makes what the flag hid usable" in system
    assert "you write it. A console screen's page is named after its route" in system


def test_a_manual_without_a_naming_rule_leaves_it_to_the_table_of_contents():
    llm = FakeLLM(submit())
    propose(llm, MR, DIFFS, MANUAL, edited=[], sha="a" * 40, repo=REPO, page_names="")
    assert "once your proposal is accepted, you write it.\nA change to how" in llm.opened[0]["system"]


def test_the_task_marks_the_pages_the_merge_request_edited():
    llm = FakeLLM(submit())
    propose(llm, MR, DIFFS, MANUAL, edited=["_devices.md"], sha="a" * 40, repo=REPO)
    assert "_devices.md (already edited in this merge request)\n    # Devices" in llm.opened[0]["task"]


def test_a_change_that_needs_no_page_changed_submits_none():
    result = propose(FakeLLM(submit()), MR, DIFFS, MANUAL, edited=[], sha="a" * 40, repo=REPO)
    assert result["outcome"] == "submitted"
    assert result["proposal"]["pages"] == []
    assert result["edited"] == {}


def test_a_missing_page_is_written_only_after_the_proposal_is_accepted():
    llm = FakeLLM(submit(EDIT, missing=[LOCATIONS]), read("_devices.md", id="r2"), write(NEW_PAGE))
    result = propose(llm, MR, DIFFS, MANUAL, edited=[], sha="a" * 40, repo=REPO)
    (opened,) = llm.opened
    assert opened["tools"] == ["read_page", "search_manual", "list_files", "grep", "read_file", "submit_proposal"]
    assert opened["added_tools"] == ["submit_new_pages"]
    (accepted,), (page_text,) = llm.sent
    assert accepted.text.startswith("Accepted. Now write the pages you named in missing_pages: _locations.md.")
    assert (f"You have at most {agent.MAX_CALLS} more tool calls (read_page, search_manual, list_files, grep, "
            "read_file and submit_new_pages together)") in accepted.text
    assert "The device list." in page_text.text
    assert [c["name"] for t in result["turns"] for c in t["calls"]] == ["submit_proposal", "read_page", "submit_new_pages"]
    assert result["edited"] == {"_policies_kiosk.md": "# Kiosk Modes\n\nLeaving kiosk mode requires the policy's exit passcode.\n"}
    assert result["writing"] == {"outcome": "submitted", "uncertainties": ["a screenshot of the map"]}
    assert result["new_pages"] == [{"page": "_locations.md", "decision": "create", "after": "_devices.md",
                                    "reason": "a new screen", "text": "# Locations\n\nThe last position each device reported.\n"}]


def test_without_missing_pages_the_accepted_proposal_ends_the_conversation():
    llm = FakeLLM(submit(EDIT))
    result = propose(llm, MR, DIFFS, MANUAL, edited=[], sha="a" * 40, repo=REPO)
    assert "added_tools" not in llm.opened[0]
    assert result["turns"][0]["calls"][0]["result"] == "accepted"
    assert result["new_pages"] == []
    assert "writing" not in result


def test_a_proposal_that_leaves_out_its_empty_lists_is_accepted():
    llm = FakeLLM(submit_tool("submit_proposal", {"reason": "a refactor", "pages": []}))
    result = propose(llm, MR, DIFFS, MANUAL, edited=[], sha="a" * 40, repo=REPO)
    assert result["outcome"] == "submitted"
    assert result["proposal"] == {"reason": "a refactor", "pages": [], "missing_pages": [], "uncertainties": []}
    assert result["new_pages"] == []


def test_a_page_the_model_cannot_write_goes_to_a_human():
    declined = {"page": "_locations.md", "decision": "needs-human", "reason": "the diff does not show the map"}
    result = propose(FakeLLM(submit(missing=[LOCATIONS]), write(declined)), MR, DIFFS, MANUAL, edited=[], sha="a" * 40, repo=REPO)
    assert result["new_pages"] == [declined]


def test_writing_that_never_validates_leaves_the_page_to_a_human():
    turns = [submit(missing=[LOCATIONS]), *(write({**NEW_PAGE, "text": "no title"}) for _ in range(agent.MAX_CALLS))]
    result = propose(FakeLLM(*turns), MR, DIFFS, MANUAL, edited=[], sha="a" * 40, repo=REPO)
    assert result["outcome"] == "submitted"
    assert result["writing"] == {"outcome": "stopped",
                                 "reason": f"no valid submit_new_pages within {agent.MAX_CALLS} tool calls"}
    assert result["new_pages"] == [{"page": "_locations.md", "decision": "needs-human", "reason":
                                    f"writing it stopped: no valid submit_new_pages within {agent.MAX_CALLS} tool calls"}]


def test_a_second_proposal_while_writing_is_refused():
    llm = FakeLLM(submit(missing=[LOCATIONS]), submit(EDIT, id="s2"), write(NEW_PAGE))
    result = propose(llm, MR, DIFFS, MANUAL, edited=[], sha="a" * 40, repo=REPO)
    assert llm.sent[1][0].text == ("your proposal is accepted already. Write the missing pages and call "
                                   "submit_new_pages")
    assert result["edited"] == {}


def test_a_missing_page_cannot_be_named_like_a_page_that_exists():
    # Whether a page is really missing is the model's call; only a file that exists cannot be created.
    assert validate(proposal(missing=[{"page": "_users.md", "describes": "roles"}]), PAGES) == (
        "_users.md exists already, so it cannot be created. Answer it in 'pages'")
    assert validate(proposal(missing=[{"page": "_roles.md", "describes": "roles"}]), PAGES) is None


def test_pages_the_model_left_alone_need_no_answer():
    result = propose(FakeLLM(submit(EDIT)), MR, DIFFS, MANUAL, edited=[], sha="a" * 40, repo=REPO)
    assert [e["page"] for e in result["proposal"]["pages"]] == ["_policies_kiosk.md"]


def test_a_broken_edit_goes_back_to_the_model_which_fixes_it():
    broken = {**EDIT, "edits": [{"find": "requires the passcode.", "replace": "x"}]}
    llm = FakeLLM(submit(broken, UNCHANGED), submit(EDIT, UNCHANGED, id="s2"))
    result = propose(llm, MR, DIFFS, MANUAL, edited=[], sha="a" * 40, repo=REPO)
    assert result["outcome"] == "submitted"
    (rejected,), = llm.sent
    assert "_policies_kiosk.md: edit 1: 'find' does not occur in the page" in rejected.text


def test_the_task_offers_the_code_at_the_merge_commit():
    llm = FakeLLM(submit(EDIT))
    propose(llm, MR, DIFFS, MANUAL, edited=[], sha="a" * 40, repo=REPO)
    task = llm.opened[0]["task"]
    assert "search the code at the merge commit with list_files, grep and read_file" in task
    assert "(read_page, search_manual, list_files, grep, read_file and submit_proposal together)" in task


def test_too_many_edited_pages_go_back_to_the_model():
    pages = {f"p{n}.md": f"text {n}\n" for n in range(MAX_EDITED_PAGES + 1)}
    entries = [{"page": p, "decision": "edit", "reason": "-", "edits": [{"find": "text", "replace": "new"}]}
               for p in pages]
    assert f"at most {MAX_EDITED_PAGES} pages may be edited" in (validate(proposal(*entries), pages) or "")
    assert validate(proposal(*entries[:MAX_EDITED_PAGES]), pages) is None


@pytest.mark.parametrize("changes, problem", [
    ({"reason": " "}, "'reason' must say what the change does for a user"),
    ({"reason": None}, "'reason' must say what the change does for a user"),
    ({"pages": None}, "'pages' must be a list, empty if no page needs changing"),
    ({"pages": [EDIT, UNCHANGED, UNCHANGED]}, "_devices.md is answered more than once"),
    ({"pages": [EDIT, {**UNCHANGED, "page": "_reports.md"}]},
     "'_reports.md' is not a page in the table of contents (a page the manual lacks goes in 'missing_pages')"),
    ({"pages": [{**EDIT, "edits": []}]}, "decision 'edit' needs at least one edit"),
    ({"pages": [EDIT, {**UNCHANGED, "edits": EDIT["edits"]}]}, "only decision 'edit' may carry edits"),
    ({"pages": [EDIT, {**UNCHANGED, "decision": "maybe"}]}, "decision must be one of"),
    ({"pages": [{**UNCHANGED, "page": ["_devices.md"]}]}, "is not a page in the table of contents"),
    ({"missing_pages": "_locations.md"}, "'missing_pages' must be a list"),
    ({"missing_pages": [{"page": "_locations.md"}]}, "every entry in 'missing_pages' needs 'page' and 'describes'"),
    ({"missing_pages": [{"page": "_devices.md", "describes": "x"}]}, "_devices.md exists already, so it cannot be created"),
])
def test_validation_names_the_problem(changes, problem):
    assert problem in (validate({**proposal(EDIT), **changes}, PAGES) or "")


def test_a_page_may_be_named_as_read_page_accepts_it():
    zulip = Manual({"docs/report-a-message.mdx": "Click **Submit**.\n"})
    entry = {"page": "report-a-message", "decision": "edit", "reason": "-",
             "edits": [{"find": "Click **Submit**.", "replace": "Click **Report**."}]}
    result = propose(FakeLLM(submit(entry)), MR, DIFFS, zulip, edited=[], sha="a" * 40, repo=REPO)
    assert result["edited"] == {"docs/report-a-message.mdx": "Click **Report**.\n"}


@pytest.mark.parametrize("changes, problem", [
    ({"pages": None}, "'pages' must be a list"),
    ({"pages": [{**NEW_PAGE, "page": "_maps.md"}]}, "'_maps.md' is not a page you named in missing_pages: _locations.md"),
    ({"pages": [NEW_PAGE, NEW_PAGE]}, "_locations.md is answered more than once"),
    ({"pages": [{**NEW_PAGE, "reason": None}]}, "_locations.md: 'reason' must say what the page describes"),
    ({"pages": [{**NEW_PAGE, "decision": "edit"}]}, "decision must be one of create, needs-human"),
    ({"pages": [{**NEW_PAGE, "decision": "needs-human"}]}, "only decision 'create' may carry text"),
    ({"pages": [{**NEW_PAGE, "text": "The last position each device reported."}]}, "needs the page's text, with its title"),
    ({"pages": [{**NEW_PAGE, "text": NEW_PAGE["text"] + "\n\n![](screenshots/_locations_1.png)"}]}, "leave images out"),
    ({"pages": [{key: value for key, value in NEW_PAGE.items() if key != "after"}]}, "needs 'after', the page it follows"),
    ({"pages": [{**NEW_PAGE, "after": "_reports.md"}]}, "_locations.md: 'after': no page '_reports.md'"),
    ({"pages": []}, "answer every page you named in missing_pages; not answered: _locations.md"),
])
def test_new_page_validation_names_the_problem(changes, problem):
    submission = {"pages": [dict(NEW_PAGE)], "uncertainties": [], **changes}
    assert problem in (validate_new_pages(submission, ["_locations.md"], MANUAL) or "")


@pytest.mark.parametrize("name", ["/etc/passwd.md", "../_locations.md"])
def test_a_missing_page_is_named_inside_the_manual(name):
    assert "name the page as the table of contents names pages" in (
        validate(proposal(missing=[{"page": name, "describes": "x"}]), PAGES) or "")
