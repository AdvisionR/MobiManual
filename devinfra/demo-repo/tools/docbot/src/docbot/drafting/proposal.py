"""Drafting: does a merge affect the manual, and if so, which pages and how.

One conversation per merge. Its input is the merge request, its diff and the
manual's table of contents. The model reads and searches the manual with
read_page and search_manual, and with a Repo it can also search the code at the
merge commit. It decides whether the change makes the manual wrong or leaves
out something new, and which pages to change. A proposal without pages is the
answer for a change that needs none; its reason says why.

The proposal is accepted when it validates: every page in the manual and
answered once, edits only with "edit", every edit applicable to its page, no
more than MAX_EDITED_PAGES pages edited, and every missing page one the manual
does not have. Only then, and only if it names missing pages, does the model
get submit_new_pages, in the same conversation and with what it has read so
far, to write those pages or hand them to a human. Deciding that a page is
missing comes first, on its own, so that writing a page is never the way
around editing the one that should change.
"""

import re

from docbot.drafting import change
from docbot.drafting.edits import EditError, apply
from docbot.drafting.manual import Manual, headings, suggest
from docbot.drafting.repo import Repo
from docbot.llm import LLM, Tool, agent
from docbot.llm.agent import ToolError

SCHEMA = "docbot.proposal/4"
PRODUCT = "MobiVisor, a mobile device management console,"
# The console's Help link opens the page named after the screen's route (public/app/help.js).
PAGE_NAMES = ("A console screen's page is named after its route, which is how the screen's Help link finds it: "
              "the route /policies/kiosk has the page _policies_kiosk.md.")
DECISIONS = ("edit", "no-change", "needs-human")
NEW_PAGE_DECISIONS = ("create", "needs-human")
# One merge rarely needs more; a proposal that edits more goes back to the model. A guard for the prototype.
MAX_EDITED_PAGES = 10

SYSTEM = """\
You keep the user manual of {product} true to what it does. You are given a merged \
change and the manual's table of contents. Decide whether the change makes the manual \
wrong, or leaves out something new its readers can now use. If it does, find the pages \
that need changing, and propose the smallest edits that make them true again.

A page needs changing only for one of these reasons:
- wrong: a sentence of the page is false once the change is merged.
- missing: the change adds a new thing a reader operates: a field, button, menu item, \
option, setting, filter, step, command, permission or shortcut. Readers can use it as \
soon as the change is merged, on a screen or in a task the page describes, and the page \
does not mention it. A change that switches a feature flag on makes what the flag hid \
usable, even if the diff shows only the flag; something added behind a flag that stays \
off is not usable yet.
The manual also lacks a page when the change adds a screen or a feature, usable as soon \
as the change is merged, that no page covers. Name such a page in missing_pages; once \
your proposal is accepted, you write it.{page_names}
A change to how something the manual already describes behaves needs an edit only if it \
makes a sentence false. A change nobody using the product can notice needs none: \
refactoring, renaming inside the code, tests, logging, performance, internal protocol \
details. If no sentence becomes false, nothing new to operate is missing and no page is \
missing, submit no pages, even when someone using the product could notice the change.

How to work:
- Use search_manual to find every page that mentions what the change touches: the \
feature, its labels, the settings or terms it changes. The table of contents alone \
can miss a page.
- Read a page with read_page before you edit it.
- Stop as soon as you know which pages need changing and how, or that none does.

Rules:
- Describe only what the change shows. Never invent behaviour, labels or steps. \
Take UI labels from the code, and write them the way the page already does.
- Describe the product as it is once the change is merged. Leave out its history \
and its plans: what it used to do, and what the merge request says will come later.
- Make the smallest edit that makes the page true. Keep the page's wording, \
structure and tone everywhere else. If the change makes a sentence wrong, correct \
that sentence; do not only add a new one next to it.
- A page marked "already edited in this merge request" was updated by the change's \
author. Leave what they wrote alone, and edit only what they missed, on that page or \
another.
- "needs-human" is the right answer for a page that must change when you cannot \
write the change from what you know.
- Name a page in missing_pages only for a screen or feature no page covers. A new \
field, option, step or setting on a screen a page describes belongs on that page.
- Never describe what belongs on a missing page on an existing page instead.
- If an image on a page may no longer match the product, say so in uncertainties, \
naming the image file. Put anything else you are unsure of there too, instead of \
guessing.

Finish by calling submit_proposal once. In reason, say in one or two sentences what \
the change does for a user, or that it does nothing a user notices. List every page \
you edit or that needs a human; you may also list pages you read and found still \
true, as "no-change". If no page needs changing, submit no pages. Each edit replaces \
an exact snippet of the page: copy "find" character for character from the text \
read_page returned, and make it long enough to occur only once. Edits to one page \
apply in order."""

SUBMIT = Tool(
    "submit_proposal",
    "Submit what the change does for a user, the pages that need changing with the edits for each, "
    "and the pages the manual lacks.",
    {"type": "object",
     "properties": {
         "reason": {"type": "string", "description": "What the change does for a user, or that it does nothing a user notices."},
         "pages": {"type": "array", "description": "Empty if no page needs changing.", "items": {
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
         "missing_pages": {"type": "array",
                           "description": "Pages the change needs that the manual does not have. You write them next.",
                           "items": {
                               "type": "object",
                               "properties": {
                                   "page": {"type": "string", "description": "A file name for the new page, as the manual names its pages."},
                                   "describes": {"type": "string", "description": "What the page will describe, and what in the change needs it."}},
                               "required": ["page", "describes"]}},
         "uncertainties": {"type": "array", "items": {"type": "string"}}},
     "required": ["reason", "pages", "missing_pages", "uncertainties"]},
)


SUBMIT_NEW_PAGES = Tool(
    "submit_new_pages",
    "Submit each page you named in missing_pages: written, or handed to a human.",
    {"type": "object",
     "properties": {
         "pages": {"type": "array", "items": {
             "type": "object",
             "properties": {
                 "page": {"type": "string", "description": "The page's name, as in missing_pages."},
                 "decision": {"type": "string", "enum": list(NEW_PAGE_DECISIONS)},
                 "after": {"type": "string", "description": "create: the page it follows in the manual's order, "
                                                            "as in the table of contents."},
                 "text": {"type": "string", "description": "create: the whole page, in Markdown."},
                 "reason": {"type": "string", "description": "What in the change the page describes, "
                                                             "or why a human has to write it."}},
             "required": ["page", "decision", "reason"]}},
         "uncertainties": {"type": "array", "items": {"type": "string"}}},
     "required": ["pages", "uncertainties"]},
)

WRITE_PAGES = """\
Accepted. Now write the pages you named in missing_pages: {pages}.

- Read a page or two like it first, and write the new one the way they are written: \
their structure, headings, tone and length.
- Describe only what the change shows, as in an edit. Take labels from the code.
- Leave out images: no screenshot of what the change adds exists yet. Name the \
screenshots a page would need in uncertainties.
- In after, name the page it follows in the manual's order, from the table of contents.
- Answer "needs-human" for a page you cannot write from what you know.

You have at most {calls} more tool calls ({tools} and submit_new_pages together). \
Call submit_new_pages when you are done."""

_IMAGE = re.compile(r"!\[|<img\b", re.IGNORECASE)


def propose(llm: LLM, mr: dict, diffs: list[dict], manual: Manual, edited: list[str], sha: str,
            repo: Repo | None = None, product: str = PRODUCT, page_names: str = PAGE_NAMES) -> dict:
    """Run the drafting conversation. `edited` names the pages the merge request edited itself.

    `page_names` tells the model how the manual names a page it lacks; empty leaves that to the
    table of contents."""
    tools, handlers = manual.tools()
    if repo:
        repo_tools, repo_handlers = repo.tools()
        tools, handlers = [*tools, *repo_tools], {**handlers, **repo_handlers}
    system = SYSTEM.format(product=product, page_names=f" {page_names}" if page_names else "")
    task = _task(mr, diffs, manual, edited, searchable=repo is not None)
    conversation = llm.conversation(system, task, [*tools, SUBMIT], cache_key=f"docbot-{sha[:12]}-draft")
    run = agent.run(conversation, handlers, SUBMIT.name,
                    lambda proposal: validate(full_names(proposal, manual), manual.pages),
                    accepted=lambda proposal: _accepted(proposal, [t.name for t in tools]))
    result = {"schema": SCHEMA, "model": llm.name, "context": "repo" if repo else "diff",
              "outcome": run["outcome"]}
    turns = run["turns"]
    if run["outcome"] != "submitted":
        return {**result, "reason": run["reason"], "system": system, "task": task, "turns": turns}

    proposal = run["submission"]
    result.update(proposal=proposal, edited=edited_pages(proposal, manual.pages), new_pages=[])
    if missing := [entry["page"] for entry in proposal["missing_pages"]]:
        conversation.add_tools([SUBMIT_NEW_PAGES])
        writing = agent.run(conversation, {**handlers, SUBMIT.name: _submitted_already}, SUBMIT_NEW_PAGES.name,
                            lambda submission: validate_new_pages(submission, missing, manual),
                            pending=run["pending"])
        turns = [*turns, *writing["turns"]]
        if writing["outcome"] == "submitted":
            result["writing"] = {"outcome": "submitted", "uncertainties": writing["submission"].get("uncertainties", [])}
            result["new_pages"] = [_new_page(entry) for entry in writing["submission"]["pages"]]
        else:
            result["writing"] = {"outcome": "stopped", "reason": writing["reason"]}
            result["new_pages"] = [{"page": page, "decision": "needs-human", "reason": f"writing it stopped: "
                                    f"{writing['reason']}"} for page in missing]
    return {**result, "system": system, "task": task, "turns": turns}


def full_names(proposal: dict, manual: Manual) -> dict:
    """The proposal, changed in place to name each page as the table of contents does.

    read_page accepts a page's name without its folder or extension, so the
    proposal may use the same short names. A name that fits no page, or
    several, is left for validate to refuse, or, as a missing page, to accept.
    """
    for key in ("pages", "missing_pages"):
        for entry in proposal.get(key) or []:
            if isinstance(entry, dict) and isinstance(entry.get("page"), str):
                try:
                    entry["page"] = manual.resolve(entry["page"])
                except ToolError:
                    pass
    return proposal


def validate(proposal: dict, pages: dict[str, str]) -> str | None:
    """None if the proposal can be applied as it stands, else what is wrong with it."""
    if not isinstance(proposal.get("reason"), str) or not proposal["reason"].strip():
        return "'reason' must say what the change does for a user"
    entries = proposal.get("pages")
    if not isinstance(entries, list):
        return "'pages' must be a list, empty if no page needs changing"
    seen = set()
    for entry in entries:
        if not isinstance(entry, dict):
            return "every entry in 'pages' must be an object"
        page, decision, edits = entry.get("page"), entry.get("decision"), entry.get("edits") or []
        if not isinstance(page, str) or page not in pages:
            return (f"{page!r} is not a page in the table of contents (a page the manual lacks goes in "
                    f"'missing_pages'){suggest(str(page), pages)}")
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
    missing = proposal.get("missing_pages", [])
    if not isinstance(missing, list):
        return "'missing_pages' must be a list, empty if the manual lacks no page"
    for entry in missing:
        if not (isinstance(entry, dict) and isinstance(entry.get("page"), str) and entry["page"].strip()
                and isinstance(entry.get("describes"), str)):
            return "every entry in 'missing_pages' needs 'page' and 'describes' strings"
        if entry["page"] in pages:
            return f"{entry['page']} is in the table of contents, so it is not missing. Answer it in 'pages'"
        if entry["page"].startswith("/") or ".." in entry["page"].split("/"):
            return f"{entry['page']!r}: name the page as the table of contents names pages"
    if not isinstance(proposal.get("uncertainties", []), list):
        return "'uncertainties' must be a list"
    return None


def validate_new_pages(submission: dict, missing: list[str], manual: Manual) -> str | None:
    """None if every missing page is written or handed to a human, else what is wrong with the submission."""
    entries = submission.get("pages")
    if not isinstance(entries, list):
        return "'pages' must be a list"
    answered = []
    for entry in entries:
        if not isinstance(entry, dict):
            return "every entry in 'pages' must be an object"
        page, decision, text = entry.get("page"), entry.get("decision"), entry.get("text")
        if page not in missing:
            return f"{page!r} is not a page you named in missing_pages: {', '.join(missing)}"
        if page in answered:
            return f"{page} is answered more than once"
        answered.append(page)
        if not isinstance(entry.get("reason"), str):
            return f"{page}: 'reason' must say what the page describes, or why a human has to write it"
        if decision not in NEW_PAGE_DECISIONS:
            return f"{page}: decision must be one of {', '.join(NEW_PAGE_DECISIONS)}"
        if decision == "needs-human":
            if text:
                return f"{page}: only decision 'create' may carry text"
            continue
        if not isinstance(text, str) or not headings(text):
            return f"{page}: decision 'create' needs the page's text, with its title"
        if _IMAGE.search(text):
            return (f"{page}: leave images out, no screenshot of what the change adds exists yet. "
                    "Name the screenshots it needs in uncertainties")
        if not isinstance(entry.get("after"), str):
            return f"{page}: decision 'create' needs 'after', the page it follows"
        try:
            entry["after"] = manual.resolve(entry["after"])
        except ToolError as e:
            return f"{page}: 'after': {e}"
    if unanswered := [page for page in missing if page not in answered]:
        return f"answer every page you named in missing_pages; not answered: {', '.join(unanswered)}"
    if not isinstance(submission.get("uncertainties", []), list):
        return "'uncertainties' must be a list"
    return None


def edited_pages(proposal: dict, pages: dict[str, str]) -> dict[str, str]:
    """The new text of every page with decision 'edit'. The proposal must have validated."""
    return {e["page"]: apply(pages[e["page"]], e["edits"]) for e in proposal["pages"] if e["decision"] == "edit"}


def _accepted(proposal: dict, tools: list[str]) -> str:
    """What an accepted proposal gets back: the task of writing its missing pages, if it names any."""
    if not proposal["missing_pages"]:
        return "accepted"
    return WRITE_PAGES.format(pages=", ".join(entry["page"] for entry in proposal["missing_pages"]),
                              calls=agent.MAX_CALLS, tools=", ".join(tools))


def _submitted_already(_: dict) -> str:
    raise ToolError("your proposal is accepted already. Write the missing pages and call submit_new_pages")


def _new_page(entry: dict) -> dict:
    """A validated entry of submit_new_pages, its text ending in one newline like every page."""
    if entry["decision"] != "create":
        return {key: entry[key] for key in ("page", "decision", "reason")}
    return {**{key: entry[key] for key in ("page", "decision", "after", "reason")},
            "text": entry["text"].rstrip("\n") + "\n"}


def _task(mr: dict, diffs: list[dict], manual: Manual, edited: list[str], searchable: bool) -> str:
    tools = "read_page, search_manual, list_files, grep and read_file" if searchable else "read_page and search_manual"
    parts = [*change.describe(mr, diffs),
             "# The manual", "", "Every page in manual order, with its headings:", "", manual.contents(edited), ""]
    if searchable:
        parts.append("You can also search the code at the merge commit with list_files, grep and read_file. "
                     "Use them when the diff alone does not tell you whether a user notices the change, "
                     "or what they see or do.")
    parts.append(f"You have at most {agent.MAX_CALLS} tool calls ({tools} and submit_proposal together). "
                 "Call submit_proposal when you have decided.")
    return "\n".join(parts)
