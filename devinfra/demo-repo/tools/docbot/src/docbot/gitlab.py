"""The GitLab API, as far as DocBot uses it. The only module that sends requests with httpx2.

Every failure to get an answer from GitLab (unreachable, 401, 5xx) raises
GitLabError, which the CLI turns into exit code 1. A 404 is not an error where
it is an answer: a commit GitLab has never seen, a file or branch that does
not exist yet.
"""

from urllib.parse import quote

import httpx2


class GitLabError(Exception):
    """GitLab could not be reached, or refused a request."""


def _enc(value: str) -> str:
    """Path-encode a project path, file path or branch name, slashes included."""
    return quote(value, safe="")


class GitLab:
    def __init__(self, url: str, project: str, token: str, transport: httpx2.BaseTransport | None = None):
        self._client = httpx2.Client(
            base_url=f"{url.rstrip('/')}/api/v4/projects/{_enc(project)}",
            headers={"PRIVATE-TOKEN": token},
            timeout=30,
            transport=transport,
        )

    def _request(self, method: str, path: str, *, tolerate: tuple[int, ...] = (), **kwargs) -> httpx2.Response:
        try:
            response = self._client.request(method, path, **kwargs)
        except httpx2.RequestError as e:
            raise GitLabError(f"{method} {path}: {e}") from e
        if response.is_error and response.status_code not in tolerate:
            raise GitLabError(f"{method} {path}: HTTP {response.status_code} {response.text[:200]}")
        return response

    def _lookup(self, path: str, **kwargs) -> httpx2.Response | None:
        """GET where a 404 is the answer "does not exist", not a failure."""
        response = self._request("GET", path, tolerate=(404,), **kwargs)
        return None if response.status_code == 404 else response

    # -- reads ---------------------------------------------------------------

    def merge_requests_for_commit(self, sha: str) -> list[dict] | None:
        """Merge requests that contain the commit, or None if GitLab has never seen it.

        An MR-<iid> build checks out a merge result built locally and never
        pushed, so a 404 here is a legitimate "not ours", not a failure.
        """
        response = self._lookup(f"repository/commits/{sha}/merge_requests")
        return None if response is None else response.json()

    def merge_request_diffs(self, iid: int) -> list[dict]:
        """Per-file diffs of a merge request, all pages."""
        diffs, page = [], "1"
        while page:
            response = self._request("GET", f"merge_requests/{iid}/diffs", params={"page": page, "per_page": 100})
            diffs += response.json()
            page = response.headers.get("X-Next-Page", "")
        return diffs

    def merge_requests_from(self, source_branch: str) -> list[dict]:
        """Every merge request, open or not, whose source is this branch."""
        response = self._request("GET", "merge_requests", params={"source_branch": source_branch, "state": "all"})
        return response.json()

    def file(self, path: str, ref: str) -> str | None:
        response = self._lookup(f"repository/files/{_enc(path)}/raw", params={"ref": ref})
        return None if response is None else response.text

    def branch_exists(self, name: str) -> bool:
        return self._lookup(f"repository/branches/{_enc(name)}") is not None

    # -- writes --------------------------------------------------------------

    def commit(self, branch: str, start_sha: str, message: str, actions: list[dict]) -> dict:
        """One commit on a new branch cut from start_sha. No clone, no push."""
        body = {"branch": branch, "start_sha": start_sha, "commit_message": message, "actions": actions}
        return self._request("POST", "repository/commits", json=body).json()

    def open_merge_request(self, source_branch: str, target_branch: str, title: str,
                           description: str, labels: list[str]) -> dict:
        body = {"source_branch": source_branch, "target_branch": target_branch, "title": title,
                "description": description, "labels": ",".join(labels)}
        return self._request("POST", "merge_requests", json=body).json()
