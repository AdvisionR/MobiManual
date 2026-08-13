"""In-memory forge.

Two jobs. It is what the test suite runs against, so the suite stays offline
(every other test here already is), and it is what `--dry-run` uses, so the
full proposal — branch name, record, merge-request body — can be produced and
read without creating anything on a real forge. The rendered body is the part
most likely to be wrong, and it is much cheaper to read it in a terminal than
in GitLab.
"""

from __future__ import annotations

from typing import Any

from . import FileChange, MergeRequestRef, Note


class FakeForge:
    name = "fake"

    def __init__(self, default_branch: str = "main", base_url: str = "https://forge.invalid") -> None:
        self._default_branch = default_branch
        self._base_url = base_url.rstrip("/")
        #: (project, branch) -> {path: content}
        self.files: dict[tuple[str, str], dict[str, str]] = {}
        self.merge_requests: list[dict[str, Any]] = []
        self.notes: list[dict[str, str]] = []
        self.commits: list[dict[str, Any]] = []

    def default_branch(self, project: str) -> str:
        return self._default_branch

    def commit(
        self,
        project: str,
        *,
        branch: str,
        start_branch: str,
        message: str,
        changes: list[FileChange],
    ) -> str:
        tree = self.files.setdefault((project, branch), dict(self.files.get((project, start_branch), {})))
        for change in changes:
            tree[change.path] = change.content
        self.commits.append(
            {"project": project, "branch": branch, "message": message,
             "paths": [c.path for c in changes]}
        )
        return f"commit{len(self.commits)}"

    def find_open_merge_request(self, project: str, *, source_branch: str) -> MergeRequestRef | None:
        for mr in self.merge_requests:
            if (mr["project"], mr["source_branch"], mr["state"]) == (project, source_branch, "opened"):
                return MergeRequestRef(
                    iid=mr["iid"], url=mr["url"], title=mr["title"],
                    state=mr["state"], source_branch=source_branch, created=False,
                )
        return None

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
        iid = str(len(self.merge_requests) + 1)
        mr = {
            "iid": iid,
            "project": project,
            "source_branch": source_branch,
            "target_branch": target_branch,
            "title": title,
            "description": description,
            "labels": list(labels or []),
            "state": "opened",
            "url": f"{self._base_url}/{project}/-/merge_requests/{iid}",
        }
        self.merge_requests.append(mr)
        return MergeRequestRef(
            iid=iid, url=mr["url"], title=title, state="opened",
            source_branch=source_branch, created=True,
        )

    def comment(self, project: str, merge_request: str, body: str) -> Note:
        self.notes.append({"project": project, "merge_request": merge_request, "body": body})
        return Note(id=str(len(self.notes)), url=f"{self._base_url}/{project}/-/merge_requests/{merge_request}")
