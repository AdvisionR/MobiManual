"""Drafting: the model reads a merge and the manual pages it may affect, and proposes edits.

One conversation per merge. Its input is the merge request, its diff and the
current text of the pages to consider. With a Repo, the model can also search
the code at the merge commit. The conversation ends when the model submits a
proposal that validates: every page answered once, edits only with "edit", and
every edit applicable to its page.

The placeholder in placeholder.py stays until update-manual uses this module.
"""

from docbot.drafting.edits import EditError, apply
from docbot.drafting.repo import Repo
from docbot.llm import LLM, Tool, agent

SCHEMA = "docbot.proposal/1"
DECISIONS = ("edit", "no-change", "needs-human")

SYSTEM = """\
You keep the user manual of MobiVisor, a mobile device management console, true to \
what the console does. You are given a merged change and the manual pages it may \
affect. For each page, decide whether the change makes it wrong or incomplete, and \
if so, propose the smallest edit that makes it true again.

Rules:
- Describe only what the change shows. Never invent behaviour, labels or steps. \
Take UI labels from the code, and write them the way the page already does, for \
example **Policies > Kiosk**.
- Make the smallest edit that makes the page true. Keep the page's wording, \
structure and tone everywhere else. If the change makes a sentence wrong, correct \
that sentence; do not only add a new one next to it.
- "no-change" is the right answer when the page is still true. "needs-human" is \
the right answer when the page must change but you cannot write it from what you \
know.
- If an image on a page may no longer match the console, say so in \
uncertainties, naming the image file. Put anything else you are unsure of there \
too, instead of guessing.

Finish by calling submit_proposal once, with one entry for every page you were \
given. Each edit replaces an exact snippet of the page: copy "find" character for \
character from the page as given, and make it long enough to occur only once. \
Edits to one page apply in order."""

SUBMIT = Tool(
    "submit_proposal",
    "Submit the decision for every page, with the edits for the pages that need them.",
    {"type": "object",
     "properties": {
         "pages": {"type": "array", "items": {
             "type": "object",
             "properties": {
                 "page": {"type": "string", "description": "The page's file name, as given."},
                 "decision": {"type": "string", "enum": list(DECISIONS)},
                 "edits": {"type": "array", "items": {
                     "type": "object",
                     "properties": {"find": {"type": "string"}, "replace": {"type": "string"}},
                     "required": ["find", "replace"]}},
                 "reason": {"type": "string", "description": "What in the change makes this necessary."}},
             "required": ["page", "decision", "reason"]}},
         "uncertainties": {"type": "array", "items": {"type": "string"}}},
     "required": ["pages", "uncertainties"]},
)


def propose(llm: LLM, mr: dict, diffs: list[dict], pages: dict[str, str], sha: str,
            repo: Repo | None = None) -> dict:
    """Run the drafting conversation. `pages` maps page file names to their current text."""
    tools, handlers = repo.tools() if repo else ([], {})
    conversation = llm.conversation(SYSTEM, _task(mr, diffs, pages, searchable=repo is not None),
                                    [*tools, SUBMIT], cache_key=f"docbot-{sha[:12]}-draft")
    run = agent.run(conversation, handlers, SUBMIT.name, lambda proposal: validate(proposal, pages))
    result = {"schema": SCHEMA, "model": llm.name, "context": "repo" if repo else "diff",
              "outcome": run["outcome"]}
    if run["outcome"] == "submitted":
        proposal = run["submission"]
        result["proposal"] = proposal
        result["edited"] = edited_pages(proposal, pages)
    else:
        result["reason"] = run["reason"]
    return {**result, "turns": run["turns"]}


def validate(proposal: dict, pages: dict[str, str]) -> str | None:
    """None if the proposal can be applied as it stands, else what is wrong with it."""
    entries = proposal.get("pages")
    if not isinstance(entries, list):
        return "'pages' must be a list"
    seen = set()
    for entry in entries:
        if not isinstance(entry, dict):
            return "every entry in 'pages' must be an object"
        page, decision, edits = entry.get("page"), entry.get("decision"), entry.get("edits") or []
        if not isinstance(page, str) or page not in pages:
            return f"{page!r} is not one of the pages given: {', '.join(pages)}"
        if page in seen:
            return f"{page} is answered more than once"
        seen.add(page)
        if decision not in DECISIONS:
            return f"{page}: decision must be one of {', '.join(DECISIONS)}"
        if decision == "edit" and not edits:
            return f"{page}: decision 'edit' needs at least one edit"
        if decision != "edit" and edits:
            return f"{page}: only decision 'edit' may carry edits"
        if not all(isinstance(e, dict) and isinstance(e.get("find"), str) and isinstance(e.get("replace"), str)
                   for e in edits):
            return f"{page}: every edit needs 'find' and 'replace' strings"
        try:
            apply(pages[page], edits)
        except EditError as e:
            return f"{page}: {e}"
    if missing := [p for p in pages if p not in seen]:
        return f"no answer for {', '.join(missing)}"
    if not isinstance(proposal.get("uncertainties", []), list):
        return "'uncertainties' must be a list"
    return None


def edited_pages(proposal: dict, pages: dict[str, str]) -> dict[str, str]:
    """The new text of every page with decision 'edit'. The proposal must have validated."""
    return {e["page"]: apply(pages[e["page"]], e["edits"]) for e in proposal["pages"] if e["decision"] == "edit"}


def _task(mr: dict, diffs: list[dict], pages: dict[str, str], searchable: bool) -> str:
    parts = [f"# Merge request !{mr['iid']}: {mr['title']}", "", (mr.get("description") or "").strip(), "",
             "# The change", ""]
    for d in diffs:
        path = d["new_path"] if d["old_path"] == d["new_path"] else f"{d['old_path']} -> {d['new_path']}"
        # Four backticks, so a diff of a Markdown file cannot close the fence.
        parts += [f"## {path}", "", "````diff", d["diff"].rstrip("\n") or "(no textual diff)", "````", ""]
    parts += ["# Manual pages to consider", ""]
    for name, text in pages.items():
        parts += [f"## {name}", "", "````markdown", text.rstrip("\n"), "````", ""]
    if searchable:
        parts += [("You can search the code at the merge commit with list_files, grep and read_file. Use them "
                   "when the diff alone does not tell you what a user sees or does, and stop searching once you "
                   f"can decide. You have at most {agent.MAX_CALLS} tool calls, submit_proposal included.")]
    else:
        parts += ["You have only the change and the pages above. Call submit_proposal when you have decided."]
    return "\n".join(parts)
