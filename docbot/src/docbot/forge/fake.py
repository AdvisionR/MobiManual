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

from . import FileChange, MergeRequestRef, MergeState, Note


class FakeForge:
    name = "fake"

    def __init__(self, default_branch: str = "main", base_url: str = "https://forge.invalid",
                 merged: bool = True, merged_by: str = "reviewer") -> None:
        self._default_branch = default_branch
        self._base_url = base_url.rstrip("/")
        #: Merged by default. `--dry-run` uses this forge to render a proposal
        #: for a merge request that has not landed yet, and refusing to render
        #: it would make the flag useless for exactly the case it previews.
        self.merge = MergeState(
            state="merged" if merged else "opened",
            merged=merged,
            merged_by=merged_by if merged else "",
            merged_at="2026-08-13T10:00:00Z" if merged else "",
            merge_commit="deadbeef" if merged else "",
            target_branch=default_branch,
        )
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

    def update_merge_request(
        self, project: str, iid: str, *, title: str, description: str
    ) -> MergeRequestRef:
        for mr in self.merge_requests:
            if mr["project"] == project and mr["iid"] == iid:
                mr["title"] = title
                mr["description"] = description
                return MergeRequestRef(
                    iid=iid, url=mr["url"], title=title, state=mr["state"],
                    source_branch=mr["source_branch"], created=False,
                )
        raise KeyError(f"no merge request {iid} in {project}")

    def merge_state(self, project: str, merge_request: str) -> MergeState:
        return self.merge

    def comment(self, project: str, merge_request: str, body: str) -> Note:
        self.notes.append({"project": project, "merge_request": merge_request, "body": body})
        return Note(id=str(len(self.notes)), url=f"{self._base_url}/{project}/-/merge_requests/{merge_request}")
