"""update-manual against a recorded GitLab and a scripted model: the whole flow, no stack, no key."""

import json
from urllib.parse import unquote

import httpx2
import pytest
from fakes import FakeLLM, submit

from docbot.gitlab import GitLab, GitLabError
from docbot.llm import agent
from docbot.update import MAX_DIFF_CHARS, update_manual

SHA = "a" * 40
PREFIX = "/api/v4/projects/root%2Fmobivisor-console/"
CODE = {"old_path": "public/app/kiosk.js", "new_path": "public/app/kiosk.js", "diff": "@@ -1 +1 @@\n+exitPasscode\n"}
SPEC = {"old_path": "e2e/kiosk.spec.js", "new_path": "e2e/kiosk.spec.js", "diff": "@@ -1 +1 @@\n+it()\n"}

FILES = {
    "doc-map.json": json.dumps({"docRoot": "public/doc", "languages": ["en", "tr", "de"],
                                "ignore": [{"id": "ci-and-tests", "code": ["^e2e/"]}]}),
    "gruntfile.js": "var htmlDocPages = [\n  '_devices.md',\n  '_users.md',\n  '_policies_kiosk.md',\n  '_devices_id.md'\n];\n",
    "public/doc/en/_devices.md": "# Devices\n\nThe device list.\n",
    "public/doc/en/_users.md": "# Users\n",
    "public/doc/en/_policies_kiosk.md": "# Kiosk Modes\n\nLeaving kiosk mode requires the device passcode.\n",
    "public/doc/en/_devices_id.md": "# Device details\n",
}

KIOSK_EDIT = {"page": "_policies_kiosk.md", "decision": "edit", "reason": "the policy has its own passcode now",
              "edits": [{"find": "the device passcode.", "replace": "the policy's exit passcode."}]}
DEVICES_EDIT = {"page": "_devices.md", "decision": "edit", "reason": "mentioned there too",
                "edits": [{"find": "The device list.", "replace": "The device list, with kiosk state."}]}


def merged(labels=(), merge_commit_sha=SHA):
    return {"iid": 4, "state": "merged", "target_branch": "main", "labels": list(labels),
            "merge_commit_sha": merge_commit_sha, "squash_commit_sha": None, "description": "A new field.",
            "title": "Give kiosk policies their own exit passcode", "author": {"username": "dev"},
            "web_url": "http://gl/mr/4"}


def drafted(*pages: dict, missing=(), uncertainties=(), reason="kiosk gains a passcode"):
    return submit("submit_proposal", {"reason": reason, "pages": list(pages), "missing_pages": list(missing),
                                      "uncertainties": list(uncertainties)}, "d1")


def written(*pages: dict, uncertainties=()):
    return submit("submit_new_pages", {"pages": list(pages), "uncertainties": list(uncertainties)}, "w1")


LOCATIONS = {"page": "_locations.md", "describes": "the Locations page"}
LOCATIONS_PAGE = {"page": "_locations.md", "decision": "create", "after": "_devices_id.md", "reason": "a new screen",
                  "text": "# Locations\n\nThe last position each device reported."}
LOCATIONS_LEFT = {"page": "_locations.md", "decision": "needs-human", "reason": "the diff does not show the map"}


class Forge:
    """GitLab, as far as update-manual uses it. Records every write."""

    def __init__(self, commit_mrs=None, existing=(), branches=(), status=200, diffs=(CODE,), files=None):
        self.commit_mrs, self.existing, self.branches, self.status = commit_mrs, list(existing), set(branches), status
        self.diffs, self.files = list(diffs), FILES if files is None else files
        self.writes = []

    def handle(self, request: httpx2.Request) -> httpx2.Response:
        if self.status != 200:
            return httpx2.Response(self.status, json={"message": "401 Unauthorized"})
        path = request.url.raw_path.decode().split("?")[0].removeprefix(PREFIX)
        if request.method == "POST":
            self.writes.append((path, json.loads(request.content)))
            return httpx2.Response(201, json={"iid": 9, "state": "opened", "web_url": "http://gl/mr/9"})
        if path == f"repository/commits/{SHA}/merge_requests" and self.commit_mrs is not None:
            return httpx2.Response(200, json=self.commit_mrs)
        if path == "merge_requests/4/diffs":
            return httpx2.Response(200, json=self.diffs)
        if path == "merge_requests":
            return httpx2.Response(200, json=self.existing)
        if path.startswith("repository/branches/") and unquote(path.split("/", 2)[2]) in self.branches:
            return httpx2.Response(200, json={})
        if path.startswith("repository/files/") and path.endswith("/raw"):
            name = unquote(path.removeprefix("repository/files/").removesuffix("/raw"))
            assert request.url.params["ref"] == SHA
            if name in self.files:
                return httpx2.Response(200, text=self.files[name])
        return httpx2.Response(404, json={"message": "404 Not Found"})


def run(forge, llm=None, **kwargs):
    gitlab = GitLab("http://gl", "root/mobivisor-console", "token", transport=httpx2.MockTransport(forge.handle))
    # A model with no turns scripted fails the test if it is asked anything.
    return update_manual(gitlab, llm or FakeLLM(), SHA, **kwargs)


def test_a_merge_opens_one_docs_merge_request_editing_every_drafted_page():
    forge = Forge(commit_mrs=[merged()])
    llm = FakeLLM(drafted(KIOSK_EDIT, DEVICES_EDIT, uncertainties=["_kiosk_mode_1.png may be stale"]))
    result = run(forge, llm)
    assert result["outcome"] == "opened"
    assert result["schema"] == "docbot.update/3"
    assert result["files"] == {"sent": ["public/app/kiosk.js"], "ignored": []}
    (commit_path, commit), (mr_path, mr) = forge.writes
    assert commit_path == "repository/commits"
    assert commit["branch"] == "docbot/mr-4"
    assert commit["start_sha"] == SHA
    assert commit["actions"] == [
        {"action": "update", "file_path": "public/doc/en/_policies_kiosk.md",
         "content": "# Kiosk Modes\n\nLeaving kiosk mode requires the policy's exit passcode.\n"},
        {"action": "update", "file_path": "public/doc/en/_devices.md",
         "content": "# Devices\n\nThe device list, with kiosk state.\n"}]
    assert mr_path == "merge_requests"
    assert mr["source_branch"] == "docbot/mr-4"
    assert mr["target_branch"] == "main"
    assert mr["labels"] == "docbot-generated"
    assert "Drafted by DocBot (fake/model) for !4" in mr["description"]
    assert "### Why the manual changes\n\nkiosk gains a passcode" in mr["description"]
    assert "- `_policies_kiosk.md`: the policy has its own passcode now" in mr["description"]
    assert "- _kiosk_mode_1.png may be stale" in mr["description"]
    assert "the tr, de translations of the edited and created pages" in mr["description"]
    assert "### Created" not in mr["description"]


def test_a_page_the_manual_lacks_is_created_and_joins_the_page_list():
    forge = Forge(commit_mrs=[merged()])
    llm = FakeLLM(drafted(KIOSK_EDIT, missing=[LOCATIONS]), written(LOCATIONS_PAGE, uncertainties=["a map screenshot"]))
    result = run(forge, llm)
    assert result["outcome"] == "opened"
    (_, commit), (_, mr) = forge.writes
    assert commit["actions"][1:] == [
        {"action": "create", "file_path": "public/doc/en/_locations.md",
         "content": "# Locations\n\nThe last position each device reported.\n"},
        {"action": "update", "file_path": "gruntfile.js",
         "content": FILES["gruntfile.js"].replace("  '_devices_id.md'\n", "  '_devices_id.md',\n  '_locations.md'\n")}]
    assert "### Created\n\n- `_locations.md`, after `_devices_id.md`: a new screen" in mr["description"]
    assert "- a map screenshot" in mr["description"]


def test_dry_run_shows_a_created_page_as_a_new_file():
    result = run(Forge(commit_mrs=[merged()]), FakeLLM(drafted(missing=[LOCATIONS]), written(LOCATIONS_PAGE)),
                 dry_run=True)
    assert result["outcome"] == "dry-run"
    assert "--- /dev/null\n+++ b/public/doc/en/_locations.md\n" in result["diff"]
    assert "+++ b/gruntfile.js" in result["diff"]
    assert "+  '_locations.md'" in result["diff"]


def test_a_page_list_docbot_cannot_add_to_is_left_to_the_reviewer():
    files = {**FILES, "gruntfile.js": FILES["gruntfile.js"].replace("'_users.md',", "'_users.md', // roles")}
    forge = Forge(commit_mrs=[merged()], files=files)
    result = run(forge, FakeLLM(drafted(missing=[LOCATIONS]), written(LOCATIONS_PAGE)))
    assert result["outcome"] == "opened"
    (_, commit), (_, mr) = forge.writes
    assert [action["file_path"] for action in commit["actions"]] == ["public/doc/en/_locations.md"]
    assert "Add the created pages to htmlDocPages in gruntfile.js by hand" in mr["description"]


def test_a_page_left_to_a_human_is_listed_next_to_the_edits():
    forge = Forge(commit_mrs=[merged()])
    run(forge, FakeLLM(drafted(KIOSK_EDIT, missing=[LOCATIONS]), written(LOCATIONS_LEFT)))
    (_, commit), (_, mr) = forge.writes
    assert [action["file_path"] for action in commit["actions"]] == ["public/doc/en/_policies_kiosk.md"]
    assert "### Needs a human\n\n- `_locations.md`: the diff does not show the map" in mr["description"]


def test_one_conversation_sees_the_table_of_contents_and_not_the_ignored_files():
    forge = Forge(commit_mrs=[merged()], diffs=[CODE, SPEC])
    llm = FakeLLM(drafted(KIOSK_EDIT))
    result = run(forge, llm)
    assert result["files"] == {"sent": ["public/app/kiosk.js"], "ignored": ["e2e/kiosk.spec.js"]}
    (opened,) = llm.opened
    assert "e2e/kiosk.spec.js" not in opened["task"]
    assert "+exitPasscode" in opened["task"]
    assert "_users.md\n    # Users" in opened["task"]
    assert "Leaving kiosk mode requires the device passcode." not in opened["task"]  # only through read_page
    assert "read_page" in opened["tools"]


@pytest.mark.parametrize("forge, reason", [
    (Forge(commit_mrs=None), "not a merge"),                                 # GitLab never saw the commit
    (Forge(commit_mrs=[merged(merge_commit_sha="b" * 40)]), "not a merge"),  # contains it, did not produce it
    (Forge(commit_mrs=[merged(labels=["docbot-generated"])]), "DocBot's own"),
    (Forge(commit_mrs=[merged()], diffs=[SPEC]), "every changed file is ignored"),
])
def test_skips_ask_no_model_and_write_nothing(forge, reason):
    result = run(forge)
    assert result["outcome"] == "skipped"
    assert reason in result["reason"]
    assert forge.writes == []


def test_a_rebuild_finds_the_docs_merge_request_it_opened_without_asking_the_model():
    forge = Forge(commit_mrs=[merged()], existing=[{"iid": 9, "state": "merged", "web_url": "http://gl/mr/9"}])
    assert run(forge)["outcome"] == "exists"
    assert forge.writes == []


def test_a_branch_left_by_an_interrupted_run_gets_its_merge_request():
    forge = Forge(commit_mrs=[merged()], branches={"docbot/mr-4"})
    assert run(forge, FakeLLM(drafted(KIOSK_EDIT)))["outcome"] == "opened"
    assert [path for path, _ in forge.writes] == ["merge_requests"]


def test_dry_run_shows_the_diff_and_writes_nothing():
    forge = Forge(commit_mrs=[merged()])
    result = run(forge, FakeLLM(drafted(KIOSK_EDIT)), dry_run=True)
    assert result["outcome"] == "dry-run"
    assert "+++ b/public/doc/en/_policies_kiosk.md" in result["diff"]
    assert "+Leaving kiosk mode requires the policy's exit passcode." in result["diff"]
    assert forge.writes == []


@pytest.mark.parametrize("turns, outcome, reason", [
    ([drafted(reason="a refactor nobody sees")], "no-doc-impact", "a refactor nobody sees"),
    ([drafted({"page": "_policies_kiosk.md", "decision": "no-change", "reason": "-"}, reason="already true")],
     "no-doc-impact", "already true"),
    ([drafted({"page": "_policies_kiosk.md", "decision": "needs-human", "reason": "-"})],
     "needs-human", "no page edited: _policies_kiosk.md needs a human"),
    ([drafted(missing=[LOCATIONS]), written(LOCATIONS_LEFT)],
     "needs-human", "no page edited: the manual has no _locations.md"),
])
def test_outcomes_without_edits_open_nothing(turns, outcome, reason):
    forge = Forge(commit_mrs=[merged()])
    result = run(forge, FakeLLM(*turns))
    assert result["outcome"] == outcome
    assert reason in result["reason"]
    assert forge.writes == []


def test_a_diff_too_large_to_send_needs_a_human_and_asks_no_model():
    big = {**CODE, "diff": "@@ -1 +1 @@\n" + "+x\n" * (MAX_DIFF_CHARS // 3)}
    forge = Forge(commit_mrs=[merged()], diffs=[big, SPEC])
    result = run(forge)
    assert result["outcome"] == "needs-human"
    assert result["reason"] == f"the diff is {MAX_DIFF_CHARS + 11} characters, more than the {MAX_DIFF_CHARS} a model is sent"
    assert result["files"] == {"sent": ["public/app/kiosk.js"], "ignored": ["e2e/kiosk.spec.js"]}
    assert forge.writes == []


def test_ignored_files_do_not_count_towards_the_size_limit():
    big = {**SPEC, "diff": "@@ -1 +1 @@\n" + "+x\n" * MAX_DIFF_CHARS}
    result = run(Forge(commit_mrs=[merged()], diffs=[CODE, big]), FakeLLM(drafted()))
    assert result["outcome"] == "no-doc-impact"


def test_a_draft_that_never_validates_needs_a_human():
    turns = [drafted(reason="") for _ in range(agent.MAX_CALLS)]
    result = run(Forge(commit_mrs=[merged()]), FakeLLM(*turns))
    assert result["outcome"] == "needs-human"
    assert result["reason"] == f"draft: no valid submit_proposal within {agent.MAX_CALLS} tool calls"


def test_a_repository_without_a_doc_map_is_an_error():
    files = {k: v for k, v in FILES.items() if k != "doc-map.json"}
    result = run(Forge(commit_mrs=[merged()], files=files))
    assert result["outcome"] == "error"
    assert result["error"] == f"doc-map.json not found at {SHA[:12]}"


def test_a_refused_token_is_an_error_not_nothing_to_do():
    with pytest.raises(GitLabError, match="HTTP 401"):
        run(Forge(status=401))
