"""GitLab forge.

Plain HTTP against the v4 REST API, matching `providers/mistral.py`: one fewer
dependency in the CI image, and a second forge is a copy of this file against a
different API rather than a second SDK.

Everything runs through the API rather than a git checkout. §8.4 warns that a
multibranch job checks out a *merge commit* over a shallow clone, which makes
local git operations quietly wrong; the commits API takes a branch name, a
start point and a list of file actions in one call, so DocBot never needs a
working copy of the docs repository at all.
"""

from __future__ import annotations

import json
from typing import Any
from urllib.parse import quote

import httpx

from ..config import forge_token
from . import FileChange, ForgeError, MergeRequestRef, MergeState, Note

TIMEOUT = 30.0


def _encode(project: str) -> str:
    """`root/mobivisor-manual` -> `root%2Fmobivisor-manual`."""
    return quote(project, safe="")


class GitLabForge:
    name = "gitlab"

    def __init__(self, url: str | None = None, token: str | None = None,
                 client: httpx.Client | None = None) -> None:
        base = (url or "").rstrip("/")
        if not base:
            raise ForgeError("no GitLab URL given (--forge-url or FORGE_URL)")
        self._api = base if base.endswith("/api/v4") else f"{base}/api/v4"
        self._token = token or forge_token()
        self._client = client

    # -- plumbing ---------------------------------------------------------

    def _request(self, method: str, path: str, **kwargs: Any) -> Any:
        if not self._token:
            raise ForgeError(
                "no forge token. Export FORGE_TOKEN, or put it in the "
                "repository-root .env. In CI it comes from withCredentials "
                "(credentialsId 'forge-bot-token', §8.5)."
            )
        url = f"{self._api}{path}"
        headers = {"PRIVATE-TOKEN": self._token}
        try:
            if self._client is not None:
                response = self._client.request(method, url, headers=headers, timeout=TIMEOUT, **kwargs)
            else:
                response = httpx.request(method, url, headers=headers, timeout=TIMEOUT, **kwargs)
        except httpx.HTTPError as exc:
            raise ForgeError(f"{method} {path} failed: {exc}") from exc

        if response.status_code == 404:
            raise ForgeError(f"{method} {path}: not found (404)")
        if response.status_code >= 400:
            raise ForgeError(f"{method} {path}: HTTP {response.status_code} — {response.text[:400]}")
        if not response.content:
            return None
        try:
            return response.json()
        except json.JSONDecodeError as exc:
            raise ForgeError(f"{method} {path}: response was not JSON — {response.text[:200]}") from exc

    def _file_exists(self, project: str, path: str, ref: str) -> bool:
        """HEAD on the files API. Decides `create` vs `update` in a commit
        action; GitLab rejects the wrong one rather than doing the sensible
        thing."""
        try:
            self._request(
                "HEAD",
                f"/projects/{_encode(project)}/repository/files/{quote(path, safe='')}",
                params={"ref": ref},
            )
        except ForgeError as exc:
            if "404" in str(exc):
                return False
            raise
        return True

    def _branch_exists(self, project: str, branch: str) -> bool:
        try:
            self._request("GET", f"/projects/{_encode(project)}/repository/branches/{quote(branch, safe='')}")
        except ForgeError as exc:
            if "404" in str(exc):
                return False
            raise
        return True

    # -- interface --------------------------------------------------------

    def default_branch(self, project: str) -> str:
        data = self._request("GET", f"/projects/{_encode(project)}")
        return str(data.get("default_branch") or "main")

    def commit(
        self,
        project: str,
        *,
        branch: str,
        start_branch: str,
        message: str,
        changes: list[FileChange],
    ) -> str:
        if not changes:
            raise ForgeError("commit called with no file changes")

        exists = self._branch_exists(project, branch)
        ref = branch if exists else start_branch
        actions = [
            {
                "action": "update" if exists and self._file_exists(project, change.path, ref) else "create",
                "file_path": change.path,
                "content": change.content,
            }
            for change in changes
        ]

        payload: dict[str, Any] = {"branch": branch, "commit_message": message, "actions": actions}
        if not exists:
            # Creates the branch as part of the commit — one call, and no
            # window in which an empty docbot/* branch exists.
            payload["start_branch"] = start_branch

        data = self._request("POST", f"/projects/{_encode(project)}/repository/commits", json=payload)
        return str(data.get("id", ""))

    def find_open_merge_request(self, project: str, *, source_branch: str) -> MergeRequestRef | None:
        data = self._request(
            "GET",
            f"/projects/{_encode(project)}/merge_requests",
            params={"source_branch": source_branch, "state": "opened"},
        )
        if not data:
            return None
        return self._ref(data[0], created=False)

    def open_merge_request(
        self,
        project: str,
        *,
        source_branch: str,
        target_branch: str,
        title: str,
        description: str,
        labels: list[str] | None = None,
    ) -> MergeRequestRef:
        payload = {
            "source_branch": source_branch,
            "target_branch": target_branch,
            "title": title,
            "description": description,
            "labels": ",".join(labels or []),
            # §7 D is rejected outright and §14.1 makes human review mandatory,
            # so the bot must never leave anything that could merge itself.
            "remove_source_branch": True,
            "squash": False,
        }
        data = self._request("POST", f"/projects/{_encode(project)}/merge_requests", json=payload)
        return self._ref(data, created=True)

    def update_merge_request(
        self, project: str, iid: str, *, title: str, description: str
    ) -> MergeRequestRef:
        data = self._request(
            "PUT",
            f"/projects/{_encode(project)}/merge_requests/{iid}",
            json={"title": title, "description": description},
        )
        return self._ref(data, created=False)

    def comment(self, project: str, merge_request: str, body: str) -> Note:
        data = self._request(
            "POST",
            f"/projects/{_encode(project)}/merge_requests/{merge_request}/notes",
            json={"body": body},
        )
        return Note(id=str(data.get("id", "")), url=str(data.get("web_url", "")))

    def merge_state(self, project: str, merge_request: str) -> MergeState:
        """`GET /merge_requests/:iid`.

        A 404 means the merge request could not be read, not that it has not
        landed — it propagates as a ForgeError so the caller can fail closed
        rather than read silence as an answer either way.
        """
        data = self._request("GET", f"/projects/{_encode(project)}/merge_requests/{merge_request}")
        return MergeState(
            state=str(data.get("state") or ""),
            merged=str(data.get("state") or "") == "merged",
            merged_by=str((data.get("merged_by") or {}).get("username", "")),
            merged_at=str(data.get("merged_at") or ""),
            # Squash and fast-forward merges leave the merge_commit_sha null
            # and put the result in squash_commit_sha instead. Recording the
            # wrong one gives the docs reviewer a sha that resolves to nothing.
            merge_commit=str(data.get("merge_commit_sha") or data.get("squash_commit_sha") or ""),
            target_branch=str(data.get("target_branch") or ""),
        )

    @staticmethod
    def _ref(data: dict[str, Any], *, created: bool) -> MergeRequestRef:
        return MergeRequestRef(
            iid=str(data.get("iid", "")),
            url=str(data.get("web_url", "")),
            title=str(data.get("title", "")),
            state=str(data.get("state", "opened")),
            source_branch=str(data.get("source_branch", "")),
            created=created,
        )
