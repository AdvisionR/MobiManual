"""update-manual against a recorded GitLab: the whole flow, no stack needed."""

import json
from urllib.parse import unquote

import httpx2
import pytest

from docbot.drafting.placeholder import MANUAL_FILE
from docbot.gitlab import GitLab, GitLabError
from docbot.update import update_manual

SHA = "a" * 40
PREFIX = "/api/v4/projects/root%2Fmobivisor-console/"


def merged(labels=(), merge_commit_sha=SHA):
    return {"iid": 4, "state": "merged", "target_branch": "main", "labels": list(labels),
            "merge_commit_sha": merge_commit_sha, "squash_commit_sha": None,
            "title": "Rework the iOS wizard", "author": {"username": "dev"}, "web_url": "http://gl/mr/4"}


class Forge:
    """GitLab, as far as update-manual uses it. Records every write."""

    def __init__(self, commit_mrs=None, existing=(), branches=(), status=200):
        self.commit_mrs, self.existing, self.branches, self.status = commit_mrs, list(existing), set(branches), status
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
            return httpx2.Response(200, json=[{"old_path": "a.js", "new_path": "a.js", "diff": "+x\n"}])
        if path == "merge_requests":
            return httpx2.Response(200, json=self.existing)
        if path.startswith("repository/branches/") and unquote(path.split("/", 2)[2]) in self.branches:
            return httpx2.Response(200, json={})
        return httpx2.Response(404, json={"message": "404 Not Found"})  # the manual file included


def run(forge, **kwargs):
    gitlab = GitLab("http://gl", "root/mobivisor-console", "token", transport=httpx2.MockTransport(forge.handle))
    return update_manual(gitlab, SHA, **kwargs)


def test_a_merge_opens_a_labelled_docs_merge_request():
    forge = Forge(commit_mrs=[merged()])
    result = run(forge)
    assert result["outcome"] == "opened"
    (commit_path, commit), (mr_path, mr) = forge.writes
    assert commit_path == "repository/commits"
    assert commit["branch"] == "docbot/mr-4"
    assert commit["start_sha"] == SHA
    assert commit["actions"][0]["action"] == "create"
    assert commit["actions"][0]["file_path"] == MANUAL_FILE
    assert mr_path == "merge_requests"
    assert mr["source_branch"] == "docbot/mr-4"
    assert mr["target_branch"] == "main"
    assert mr["labels"] == "docbot-generated"


@pytest.mark.parametrize("forge, reason", [
    (Forge(commit_mrs=None), "not a merge"),                                 # GitLab never saw the commit
    (Forge(commit_mrs=[merged(merge_commit_sha="b" * 40)]), "not a merge"),  # contains it, did not produce it
    (Forge(commit_mrs=[merged(labels=["docbot-generated"])]), "DocBot's own"),
])
def test_skips_write_nothing(forge, reason):
    result = run(forge)
    assert result["outcome"] == "skipped"
    assert reason in result["reason"]
    assert forge.writes == []


def test_a_rebuild_finds_the_docs_merge_request_it_opened():
    forge = Forge(commit_mrs=[merged()], existing=[{"iid": 9, "state": "merged", "web_url": "http://gl/mr/9"}])
    assert run(forge)["outcome"] == "exists"
    assert forge.writes == []


def test_a_branch_left_by_an_interrupted_run_gets_its_merge_request():
    forge = Forge(commit_mrs=[merged()], branches={"docbot/mr-4"})
    assert run(forge)["outcome"] == "opened"
    assert [path for path, _ in forge.writes] == ["merge_requests"]


def test_dry_run_shows_the_diff_and_writes_nothing():
    forge = Forge(commit_mrs=[merged()])
    result = run(forge, dry_run=True)
    assert result["outcome"] == "dry-run"
    assert f"+++ b/{MANUAL_FILE}" in result["diff"]
    assert "+## !4: Rework the iOS wizard" in result["diff"]
    assert forge.writes == []


def test_a_refused_token_is_an_error_not_nothing_to_do():
    with pytest.raises(GitLabError, match="HTTP 401"):
        run(Forge(status=401))
