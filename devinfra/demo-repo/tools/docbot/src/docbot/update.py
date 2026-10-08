"""update-manual: one merge to main in, at most one docs merge request out.

Idempotent, keyed on the source merge request: its docs merge request always
comes from branch docbot/mr-<iid>, so a rebuild finds the one it opened before
instead of opening a second, and asks no model.

Between resolving the merge and publishing, two conversations decide: triage
says whether the merge affects the manual at all, and drafting finds the pages
it affects and edits them. An outcome without edits opens no merge request and
is recorded in the result only.
"""

import difflib
import json

from docbot.drafting import ignore, manual, triage
from docbot.drafting.proposal import propose
from docbot.drafting.repo import Repo
from docbot.gitlab import GitLab
from docbot.llm import LLM
from docbot.resolve import resolve

SCHEMA = "docbot.update/2"
TARGET_BRANCH = "main"
GENERATED_LABEL = "docbot-generated"
DOC_MAP = "doc-map.json"
GRUNTFILE = "gruntfile.js"
# The most diff the model is sent, in characters (about 25k tokens)
MAX_DIFF_CHARS = 100_000


def update_manual(gitlab: GitLab, llm: LLM, sha: str, dry_run: bool = False, repo: Repo | None = None) -> dict:
    result: dict = {"schema": SCHEMA, "sha": sha}

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
        return {**result, "outcome": "exists", "docs_merge_request": _ref(existing[0])}

    doc_map_text = gitlab.file(DOC_MAP, ref=sha)
    gruntfile = gitlab.file(GRUNTFILE, ref=sha)
    if doc_map_text is None or gruntfile is None:
        missing = DOC_MAP if doc_map_text is None else GRUNTFILE
        return {**result, "outcome": "error", "error": f"{missing} not found at {sha[:12]}"}
    doc_map = json.loads(doc_map_text)
    page_dir = f"{doc_map['docRoot']}/{manual.LANGUAGE}"

    selection = ignore.select(doc_map, gitlab.merge_request_diffs(mr["iid"]), page_dir)
    result["files"] = {"sent": [d["new_path"] for d in selection.relevant], "ignored": selection.ignored}
    if not selection.relevant:
        return {**result, "outcome": "skipped", "reason": f"every changed file is ignored by {DOC_MAP}"}
    size = sum(len(d["diff"]) for d in selection.relevant)
    if size > MAX_DIFF_CHARS:
        return {**result, "outcome": "needs-human",
                "reason": f"the diff is {size} characters, more than the {MAX_DIFF_CHARS} a model is sent"}

    names = manual.html_doc_pages(gruntfile)
    texts = {name: gitlab.file(f"{page_dir}/{name}", ref=sha) for name in names}
    the_manual = manual.Manual({name: text for name, text in texts.items() if text is not None})

    triaged = triage.triage(llm, mr, selection.relevant, the_manual, selection.edited_pages, sha)
    result["triage"] = triaged
    if triaged["outcome"] != "submitted":
        return {**result, "outcome": "needs-human", "reason": f"triage: {triaged['reason']}"}
    answer = triaged["answer"]
    if answer["decision"] == "no-doc-impact":
        return {**result, "outcome": "no-doc-impact", "reason": answer["reason"]}

    pages = the_manual.pages
    drafted = propose(llm, mr, selection.relevant, the_manual, selection.edited_pages, sha, repo=repo)
    result["draft"] = drafted
    if drafted["outcome"] != "submitted":
        return {**result, "outcome": "needs-human", "reason": f"draft: {drafted['reason']}"}
    proposal, edited = drafted["proposal"], drafted["edited"]
    if not edited:
        if any(entry["decision"] == "needs-human" for entry in proposal["pages"]):
            return {**result, "outcome": "needs-human", "reason": "no page edited, at least one needs a human"}
        return {**result, "outcome": "no-change", "reason": "drafting found nothing to change"}

    result["diff"] = "".join(_unified(f"{page_dir}/{name}", pages[name], new) for name, new in edited.items())
    if dry_run:
        return {**result, "outcome": "dry-run"}

    # A branch with no merge request means an earlier run stopped between the two writes.
    if not gitlab.branch_exists(branch):
        gitlab.commit(branch, start_sha=sha, message=f"Manual update for !{mr['iid']} (DocBot)",
                      actions=[{"action": "update", "file_path": f"{page_dir}/{name}", "content": new}
                               for name, new in edited.items()])
    opened = gitlab.open_merge_request(
        source_branch=branch, target_branch=TARGET_BRANCH,
        title=f"Manual update for !{mr['iid']}: {mr['title']}",
        description=_description(mr, llm.name, answer, proposal, doc_map), labels=[GENERATED_LABEL])
    return {**result, "outcome": "opened", "docs_merge_request": _ref(opened)}


def _ref(mr: dict) -> dict:
    return {"iid": mr["iid"], "state": mr["state"], "url": mr["web_url"]}


def _unified(path: str, old: str, new: str) -> str:
    return "".join(difflib.unified_diff(old.splitlines(keepends=True), new.splitlines(keepends=True),
                                        fromfile=f"a/{path}", tofile=f"b/{path}"))


def _description(mr: dict, model: str, answer: dict, proposal: dict, doc_map: dict) -> str:
    """Where the model's reasoning reaches the reviewer."""
    by_decision: dict[str, list[str]] = {}
    for entry in proposal["pages"]:
        by_decision.setdefault(entry["decision"], []).append(f"- `{entry['page']}`: {entry['reason']}")
    sections = [f"Drafted by DocBot ({model}) for !{mr['iid']}: {mr['web_url']}",
                "### Why the manual changes\n\n" + answer["reason"]]
    for decision, heading in (("edit", "Edited"), ("needs-human", "Needs a human"), ("no-change", "Unchanged")):
        if decision in by_decision:
            sections.append(f"### {heading}\n\n" + "\n".join(by_decision[decision]))
    if uncertainties := proposal.get("uncertainties"):
        sections.append("### Uncertain\n\n" + "\n".join(f"- {u}" for u in uncertainties))
    if others := [lang for lang in doc_map.get("languages", []) if lang != manual.LANGUAGE]:
        sections.append(f"Not updated: the {', '.join(others)} translations of the edited pages.")
    sections.append("Nothing merges itself: review it, then merge or close.")
    return "\n\n".join(sections)
