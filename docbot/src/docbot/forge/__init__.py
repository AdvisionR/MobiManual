"""Forges behind a thin interface — foundation doc §8.1, §12 question #1.

Which forge the real MobiVisor repository lives on is still open: GitLab,
Bitbucket, or GitHub Enterprise. §8.1 says that choice "decides the plugin and
nothing else", and this module is where that claim is made true — everything
above it works in merge-request abstractions, not in GitLab URLs.

The interface is as narrow as delivery model B needs (§7): put a file on a
branch, open a merge request for it, find the one already open, and comment
back on the source merge request. Nothing here knows what a doc-impact record
is; that is propose.py.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


class ForgeError(RuntimeError):
    """The forge refused or could not be reached. Always surfaced, never
    swallowed: a proposal that silently failed to open is indistinguishable
    from a gate that stayed correctly quiet, and the two must never be
    confused."""


@dataclass
class FileChange:
    path: str
    content: str


@dataclass
class MergeRequestRef:
    """A merge request on the docs repository."""

    iid: str
    url: str
    title: str = ""
    state: str = "opened"
    source_branch: str = ""
    #: False when this call found an existing merge request rather than
    #: opening one. Re-running the gate on a pushed-to source MR must not
    #: produce a second docs MR.
    created: bool = True


@dataclass
class Note:
    """A comment posted on a merge request."""

    id: str = ""
    url: str = ""


@dataclass
class MergeState:
    """Whether a source merge request has actually landed.

    `state` is the forge's own word — `opened`, `merged`, `closed`, `locked` —
    and `merged` is the only one DocBot acts on. The distinction between the
    other three matters for what it says afterwards: `opened` is "not yet",
    while `closed` is "never", and a queue that cannot tell them apart
    accumulates entries nobody will ever clear.
    """

    state: str = ""
    merged: bool = False
    merged_by: str = ""
    merged_at: str = ""
    merge_commit: str = ""
    target_branch: str = ""


class Forge(Protocol):
    name: str

    def default_branch(self, project: str) -> str: ...

    def commit(
        self,
        project: str,
        *,
        branch: str,
        start_branch: str,
        message: str,
        changes: list[FileChange],
    ) -> str:
        """Create or update `changes` on `branch`, branching from
        `start_branch` if it does not exist. Returns the commit id."""
        ...

    def find_open_merge_request(self, project: str, *, source_branch: str) -> MergeRequestRef | None: ...

    def open_merge_request(
        self,
        project: str,
        *,
        source_branch: str,
        target_branch: str,
        title: str,
        description: str,
        labels: list[str] = ...,
    ) -> MergeRequestRef: ...

    def update_merge_request(
        self, project: str, iid: str, *, title: str, description: str
    ) -> MergeRequestRef:
        """Refresh an existing proposal. A source MR pushed to twice keeps one
        docs MR, so the body has to be rewritten or it describes the first
        verdict forever."""
        ...

    def comment(self, project: str, merge_request: str, body: str) -> Note: ...

    def merge_state(self, project: str, merge_request: str) -> MergeState:
        """Has this merge request landed? Raise ForgeError when the forge
        cannot say — callers must be able to tell "not merged" from "could not
        find out"."""
        ...


def get(name: str, **kwargs: object) -> Forge:
    if name == "gitlab":
        from .gitlab import GitLabForge

        return GitLabForge(**kwargs)  # type: ignore[arg-type]
    if name == "fake":
        from .fake import FakeForge

        return FakeForge(**kwargs)  # type: ignore[arg-type]
    raise ForgeError(f"unknown forge {name!r} (known: gitlab, fake)")


__all__ = [
    "FileChange",
    "Forge",
    "ForgeError",
    "MergeRequestRef",
    "MergeState",
    "Note",
    "get",
]
