"""update-manual: one merge to main in, one docs merge request out.

Idempotent, keyed on the source merge request: its docs merge request always
comes from branch docbot/mr-<iid>, so a rebuild finds the one it opened before
instead of opening a second.
"""

import difflib

from docbot.draft import MANUAL_FILE, draft
from docbot.gitlab import GitLab
from docbot.resolve import resolve

TARGET_BRANCH = "main"
GENERATED_LABEL = "docbot-generated"


def update_manual(gitlab: GitLab, sha: str, dry_run: bool = False) -> dict:
    result: dict = {"schema": "docbot.update/1", "sha": sha}

    mr = resolve(gitlab, sha, TARGET_BRANCH)
    if mr is None:
        return {**result, "outcome": "skipped", "reason": f"not a merge to {TARGET_BRANCH}"}
    result["source"] = {"iid": mr["iid"], "title": mr["title"],
                        "author": mr["author"]["username"], "url": mr["web_url"]}

    # Skip docbot mr
    if GENERATED_LABEL in mr["labels"]:
        return {**result, "outcome": "skipped", "reason": f"DocBot's own merge request ({GENERATED_LABEL})"}

    branch = f"docbot/mr-{mr['iid']}"
    result["branch"] = branch
    existing = gitlab.merge_requests_from(branch)
    if existing:
        return {**result, "outcome": "exists", "merge_request": _ref(existing[0])}

    current = gitlab.file(MANUAL_FILE, ref=sha)
    new = draft(current, mr, gitlab.merge_request_diffs(mr["iid"]))
    result["diff"] = _unified(current or "", new)
    if dry_run:
        return {**result, "outcome": "dry-run"}

    # A branch with no merge request means an earlier run stopped between the two writes.
    if not gitlab.branch_exists(branch):
        action = "create" if current is None else "update"
        gitlab.commit(branch, start_sha=sha, message=f"Manual update for !{mr['iid']} (DocBot placeholder)",
                      actions=[{"action": action, "file_path": MANUAL_FILE, "content": new}])
    opened = gitlab.open_merge_request(
        source_branch=branch, target_branch=TARGET_BRANCH,
        title=f"Manual update for !{mr['iid']}: {mr['title']}",
        description=_description(mr), labels=[GENERATED_LABEL])
    return {**result, "outcome": "opened", "merge_request": _ref(opened)}


def _ref(mr: dict) -> dict:
    return {"iid": mr["iid"], "state": mr["state"], "url": mr["web_url"]}


def _unified(old: str, new: str) -> str:
    return "".join(difflib.unified_diff(old.splitlines(keepends=True), new.splitlines(keepends=True),
                                        fromfile=f"a/{MANUAL_FILE}", tofile=f"b/{MANUAL_FILE}"))


def _description(mr: dict) -> str:
    return (f"Placeholder written by DocBot for !{mr['iid']}: {mr['web_url']}\n\n"
            f"It appends that merge request's diff to `{MANUAL_FILE}`. The drafting agent "
            "will edit the affected manual pages instead.\n\n"
            "Nothing merges itself: review it, then merge or close.")
