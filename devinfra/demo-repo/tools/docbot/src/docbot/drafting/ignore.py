"""Which changed files the model sees: the doc map's ignore list. Pure.

doc-map.json, read at the merge commit, lists path patterns whose changes never
call for a manual update: tests, CI, DocBot itself, the manual. Those diffs are
dropped before any model sees the merge request, and a merge that touches
nothing else ends there. The ignore list decides only that; which pages a
change affects is the model's call.

Manual pages the merge request edited itself are dropped from the diff like
the rest of the manual, but remembered, so triage can be told which pages the
author already updated.
"""

import re
from dataclasses import dataclass


@dataclass(frozen=True)
class Selection:
    relevant: list[dict]  # the diffs the model sees
    ignored: list[str]  # the paths dropped, for the log
    edited_pages: list[str]  # pages under page_dir that the merge request edited


def select(doc_map: dict, diffs: list[dict], page_dir: str) -> Selection:
    """Split a merge request's diffs by the doc map. page_dir is the manual's English directory."""
    patterns = [re.compile(code) for entry in doc_map.get("ignore", []) for code in entry.get("code", [])]

    def ignored(path: str) -> bool:
        return any(p.search(path) for p in patterns)

    relevant, dropped, edited = [], [], []
    for d in diffs:
        # A rename matters if either side does: moving a file out of an ignored area is a change.
        if ignored(d["old_path"]) and ignored(d["new_path"]):
            dropped.append(d["new_path"])
        else:
            relevant.append(d)
        if d["new_path"].startswith(f"{page_dir}/") and not d.get("deleted_file"):
            edited.append(d["new_path"].removeprefix(f"{page_dir}/"))
    return Selection(relevant, dropped, edited)
