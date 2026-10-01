"""Drafting: the model finds the manual pages a merge affects, and proposes edits to them.

One conversation per merge, after triage has found doc impact. Its input is
the merge request, its diff and the manual's table of contents. The model
reads and searches the manual with read_page and search_manual, and decides
itself which pages to change. With a Repo, it can also search the code at the
merge commit. The conversation ends when the model submits a proposal that
validates: every page in the manual and answered once, edits only with
"edit", every edit applicable to its page, and no more than MAX_EDITED_PAGES
pages edited.
"""

from docbot.drafting import change
from docbot.drafting.edits import EditError, apply
from docbot.drafting.manual import Manual, suggest
from docbot.drafting.repo import Repo
from docbot.drafting.triage import PRODUCT
from docbot.llm import LLM, Tool, agent
from docbot.llm.agent import ToolError

SCHEMA = "docbot.proposal/2"
DECISIONS = ("edit", "no-change", "needs-human")
# One merge rarely needs more; a proposal that edits more goes back to the model. A guard for the prototype.
MAX_EDITED_PAGES = 5

SYSTEM = """\
You keep the user manual of {product} true to what it does. You are given a merged \
change that changes what the manual should say, and the manual's table of contents. \
Find the pages the change makes wrong or incomplete, and propose the smallest edits \
that make them true again.

How to work:
- Use search_manual to find every page that mentions what the change touches: the \
feature, its labels, the settings or terms it changes. The table of contents alone \
can miss a page.
- Read a page with read_page before you edit it.
- Stop as soon as you know which pages need changing and how.

Rules:
- Describe only what the change shows. Never invent behaviour, labels or steps. \
Take UI labels from the code, and write them the way the page already does.
- Make the smallest edit that makes the page true. Keep the page's wording, \
structure and tone everywhere else. If the change makes a sentence wrong, correct \
that sentence; do not only add a new one next to it.
- "needs-human" is the right answer for a page that must change when you cannot \
write the change from what you know.
- You cannot create pages. If the change needs a page the manual does not have, say \
so in uncertainties.
- If an image on a page may no longer match the product, say so in uncertainties, \
naming the image file. Put anything else you are unsure of there too, instead of \
guessing.

Finish by calling submit_proposal once. List every page you edit or that needs a \
human; you may also list pages you read and found still true, as "no-change". Each \
edit replaces an exact snippet of the page: copy "find" character for character \
from the text read_page returned, and make it long enough to occur only once. \
Edits to one page apply in order."""

SUBMIT = Tool(
    "submit_proposal",
    "Submit the pages that need changing, with the edits for each.",
    {"type": "object",
     "properties": {
         "pages": {"type": "array", "items": {
             "type": "object",
             "properties": {
                 "page": {"type": "string", "description": "The page's name, as in the table of contents."},
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


def propose(llm: LLM, mr: dict, diffs: list[dict], manual: Manual, edited: list[str], sha: str,
            repo: Repo | None = None, product: str = PRODUCT) -> dict:
    """Run the drafting conversation. `edited` names the pages the merge request edited itself."""
    tools, handlers = manual.tools()
    if repo:
        repo_tools, repo_handlers = repo.tools()
        tools, handlers = [*tools, *repo_tools], {**handlers, **repo_handlers}
    conversation = llm.conversation(SYSTEM.format(product=product),
                                    _task(mr, diffs, manual, edited, searchable=repo is not None),
                                    [*tools, SUBMIT], cache_key=f"docbot-{sha[:12]}-draft")
    run = agent.run(conversation, handlers, SUBMIT.name,
                    lambda proposal: validate(full_names(proposal, manual), manual.pages))
    result = {"schema": SCHEMA, "model": llm.name, "context": "repo" if repo else "diff",
              "outcome": run["outcome"]}
    if run["outcome"] == "submitted":
        proposal = run["submission"]
        result["proposal"] = proposal
        result["edited"] = edited_pages(proposal, manual.pages)
    else:
        result["reason"] = run["reason"]
    return {**result, "turns": run["turns"]}


def full_names(proposal: dict, manual: Manual) -> dict:
    """The proposal, changed in place to name each page as the table of contents does.

    read_page accepts a page's name without its folder or extension, so the
    proposal may use the same short names. A name that fits no page, or
    several, is left for validate to refuse.
    """
    for entry in proposal.get("pages") or []:
        if isinstance(entry, dict) and isinstance(entry.get("page"), str):
            try:
                entry["page"] = manual.resolve(entry["page"])
            except ToolError:
                pass
    return proposal


def validate(proposal: dict, pages: dict[str, str]) -> str | None:
    """None if the proposal can be applied as it stands, else what is wrong with it."""
    entries = proposal.get("pages")
    if not isinstance(entries, list) or not entries:
        return "'pages' must list at least one page"
    seen = set()
    for entry in entries:
        if not isinstance(entry, dict):
            return "every entry in 'pages' must be an object"
        page, decision, edits = entry.get("page"), entry.get("decision"), entry.get("edits") or []
        if not isinstance(page, str) or page not in pages:
            return f"{page!r} is not a page in the table of contents{suggest(str(page), pages)}"
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
    if sum(e["decision"] == "edit" for e in entries) > MAX_EDITED_PAGES:
        return (f"at most {MAX_EDITED_PAGES} pages may be edited in one proposal. Edit the ones that matter most "
                "and answer 'needs-human' for the rest")
    if not isinstance(proposal.get("uncertainties", []), list):
        return "'uncertainties' must be a list"
    return None


def edited_pages(proposal: dict, pages: dict[str, str]) -> dict[str, str]:
    """The new text of every page with decision 'edit'. The proposal must have validated."""
    return {e["page"]: apply(pages[e["page"]], e["edits"]) for e in proposal["pages"] if e["decision"] == "edit"}


def _task(mr: dict, diffs: list[dict], manual: Manual, edited: list[str], searchable: bool) -> str:
    tools = "read_page, search_manual, list_files, grep and read_file" if searchable else "read_page and search_manual"
    parts = [*change.describe(mr, diffs),
             "# The manual", "", "Every page in manual order, with its headings:", "", manual.contents(edited), ""]
    if searchable:
        parts.append("You can also search the code at the merge commit with list_files, grep and read_file. "
                     "Use them when the diff alone does not tell you what a user sees or does.")
    parts.append(f"You have at most {agent.MAX_CALLS} tool calls ({tools} and submit_proposal together). "
                 "Call submit_proposal when you have decided.")
    return "\n".join(parts)
