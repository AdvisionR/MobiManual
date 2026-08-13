"""The GitLab forge, against a mocked transport.

These exist for one reason: the API's create/update distinction is the kind of
detail that only fails on the second run, in CI, against a branch that already
exists. That is an expensive place to discover it.
"""

from __future__ import annotations

import json

import httpx
import pytest

from docbot.forge import FileChange, ForgeError
from docbot.forge.gitlab import GitLabForge

PROJECT = "root/mobivisor-manual"
ENCODED = "root%2Fmobivisor-manual"


class Recorder:
    """Routes requests by (method, path) and records what was sent."""

    def __init__(self, routes: dict[tuple[str, str], object], missing: set[str] = frozenset()):
        self.routes = routes
        self.missing = set(missing)
        self.calls: list[httpx.Request] = []

    def __call__(self, request: httpx.Request) -> httpx.Response:
        self.calls.append(request)
        # raw_path, not path: GitLab identifies a project by a percent-encoded
        # `group/name`, and httpx decodes `.path` back to a slash.
        raw = request.url.raw_path.decode().split("?", 1)[0]
        path = raw.split("/api/v4", 1)[-1]
        if path in self.missing:
            return httpx.Response(404, json={"message": "404 Not Found"})
        body = self.routes.get((request.method, path))
        if body is None:
            return httpx.Response(404, json={"message": f"no route for {request.method} {path}"})
        return httpx.Response(200, json=body)

    def sent(self, method: str, path: str) -> dict:
        for call in self.calls:
            if call.method == method and call.url.path.endswith(path):
                return json.loads(call.content)
        raise AssertionError(f"no {method} to {path} was made")


def build(recorder: Recorder) -> GitLabForge:
    client = httpx.Client(transport=httpx.MockTransport(recorder))
    return GitLabForge(url="http://gitlab.orb.local", token="t", client=client)


def test_first_commit_creates_the_branch_and_the_file():
    recorder = Recorder(
        routes={("POST", f"/projects/{ENCODED}/repository/commits"): {"id": "abc123"}},
        missing={f"/projects/{ENCODED}/repository/branches/docbot%2Fmr-12"},
    )
    sha = build(recorder).commit(
        PROJECT, branch="docbot/mr-12", start_branch="main",
        message="Doc impact record", changes=[FileChange("doc-impact/pending/mr-12.yaml", "x: 1")],
    )

    assert sha == "abc123"
    payload = recorder.sent("POST", "/repository/commits")
    assert payload["start_branch"] == "main"           # the branch is created here
    assert payload["actions"][0]["action"] == "create"


def test_second_commit_updates_the_existing_file():
    """Same source MR, pushed to again. GitLab rejects `create` on a file that
    exists, so the action has to flip."""
    recorder = Recorder(
        routes={
            ("GET", f"/projects/{ENCODED}/repository/branches/docbot%2Fmr-12"): {"name": "docbot/mr-12"},
            ("HEAD", f"/projects/{ENCODED}/repository/files/doc-impact%2Fpending%2Fmr-12.yaml"): {},
            ("POST", f"/projects/{ENCODED}/repository/commits"): {"id": "def456"},
        }
    )
    build(recorder).commit(
        PROJECT, branch="docbot/mr-12", start_branch="main",
        message="Doc impact record", changes=[FileChange("doc-impact/pending/mr-12.yaml", "x: 2")],
    )

    payload = recorder.sent("POST", "/repository/commits")
    assert payload["actions"][0]["action"] == "update"
    assert "start_branch" not in payload                # it already exists


def test_existing_open_merge_request_is_found():
    recorder = Recorder(
        routes={
            ("GET", f"/projects/{ENCODED}/merge_requests"): [
                {"iid": 4, "web_url": "http://gitlab/mr/4", "title": "Doc impact", "state": "opened"}
            ]
        }
    )
    found = build(recorder).find_open_merge_request(PROJECT, source_branch="docbot/mr-12")

    assert found is not None
    assert (found.iid, found.created) == ("4", False)


def test_no_open_merge_request_returns_none():
    recorder = Recorder(routes={("GET", f"/projects/{ENCODED}/merge_requests"): []})
    assert build(recorder).find_open_merge_request(PROJECT, source_branch="docbot/mr-12") is None


def test_opened_merge_request_cannot_merge_itself():
    """§7 rejects option D; nothing DocBot opens may be set up to auto-merge."""
    recorder = Recorder(
        routes={("POST", f"/projects/{ENCODED}/merge_requests"):
                {"iid": 9, "web_url": "http://gitlab/mr/9", "title": "t", "state": "opened"}}
    )
    build(recorder).open_merge_request(
        PROJECT, source_branch="docbot/mr-12", target_branch="main",
        title="t", description="d", labels=["docbot", "doc-impact"],
    )

    payload = recorder.sent("POST", "/merge_requests")
    assert payload["labels"] == "docbot,doc-impact"
    assert payload["target_branch"] == "main"
    assert "merge_when_pipeline_succeeds" not in payload


def test_merge_state_reads_a_merged_request():
    recorder = Recorder(
        routes={("GET", f"/projects/{ENCODED}/merge_requests/4"): {
            "state": "merged",
            "merged_by": {"username": "alice"},
            "merged_at": "2026-08-13T10:00:00Z",
            "merge_commit_sha": "abc123",
            "target_branch": "main",
        }}
    )
    state = build(recorder).merge_state(PROJECT, "4")

    assert state.merged is True
    assert (state.merged_by, state.merge_commit, state.target_branch) == ("alice", "abc123", "main")


def test_squash_merges_report_the_squash_commit():
    """Squash and fast-forward merges leave merge_commit_sha null. Recording
    that verbatim hands the docs reviewer a sha that resolves to nothing."""
    recorder = Recorder(
        routes={("GET", f"/projects/{ENCODED}/merge_requests/4"): {
            "state": "merged",
            "merge_commit_sha": None,
            "squash_commit_sha": "5quash3d",
            "target_branch": "main",
        }}
    )
    assert build(recorder).merge_state(PROJECT, "4").merge_commit == "5quash3d"


def test_open_and_closed_are_both_not_merged_but_distinguishable():
    for state_name in ("opened", "closed"):
        recorder = Recorder(
            routes={("GET", f"/projects/{ENCODED}/merge_requests/4"): {"state": state_name}}
        )
        state = build(recorder).merge_state(PROJECT, "4")
        assert state.merged is False
        assert state.state == state_name


def test_unreadable_merge_request_raises_rather_than_reporting_unmerged():
    """A forge that cannot answer must be distinguishable from a merge request
    that has not landed: the caller defers on both, but only one is a bug."""
    recorder = Recorder(routes={}, missing={f"/projects/{ENCODED}/merge_requests/4"})
    with pytest.raises(ForgeError, match="404"):
        build(recorder).merge_state(PROJECT, "4")


def test_http_errors_surface_rather_than_pass_silently():
    """A proposal that quietly failed to open looks exactly like a gate that
    correctly said nothing."""

    def unauthorised(request: httpx.Request) -> httpx.Response:
        return httpx.Response(401, text="401 Unauthorized")

    forge = GitLabForge(url="http://gitlab.orb.local", token="bad",
                        client=httpx.Client(transport=httpx.MockTransport(unauthorised)))
    with pytest.raises(ForgeError, match="401"):
        forge.default_branch(PROJECT)


def test_missing_token_is_a_clear_error_not_a_401():
    forge = GitLabForge(url="http://gitlab.orb.local", token="")
    with pytest.raises(ForgeError, match="FORGE_TOKEN"):
        forge.default_branch(PROJECT)


@pytest.mark.parametrize("url", [
    "http://gitlab.orb.local",
    "http://gitlab.orb.local/",
    "http://gitlab.orb.local/api/v4",   # what someone copies out of the docs
])
def test_url_may_already_carry_the_api_suffix(url):
    recorder = Recorder(routes={("GET", f"/projects/{ENCODED}"): {"default_branch": "main"}})
    forge = GitLabForge(url=url, token="t",
                        client=httpx.Client(transport=httpx.MockTransport(recorder)))
    assert forge.default_branch(PROJECT) == "main"


def test_no_url_is_refused_up_front():
    with pytest.raises(ForgeError, match="no GitLab URL"):
        GitLabForge(url="", token="t")
