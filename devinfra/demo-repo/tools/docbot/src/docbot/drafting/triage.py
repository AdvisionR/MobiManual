"""Triage: does a merged change affect the manual at all?

One conversation per merge, before drafting. The model reads the whole
manual, the merge request and its diff, and answers doc-impact or
no-doc-impact, with a reason. A doc-impact answer points at the manual: a
sentence the change makes wrong, a passage a new thing belongs next to, or a
page the manual lacks. Which pages to change is drafting's call, not
triage's. Its only tool is submit_triage; the conversation ends when an
answer validates.

Only what can be looked up is checked: that a page named in the evidence is in
the manual, and that its quote is on that page. Whether the evidence is right
is the model's call. Checks that judged it (a label must be on an added line,
not on a removed one, not only in comments; a quote must not be the author's
own line) turned a right answer wrong for Large 4 and caught nothing it got
wrong (2026-10-13, docs/docbot-large-4-narrow2.md in the MobiManual repository).
"""

import re

from docbot.drafting import change
from docbot.drafting.manual import Manual
from docbot.llm import LLM, Tool, agent
from docbot.llm.agent import ToolError

SCHEMA = "docbot.triage/4"
PRODUCT = "MobiVisor, a mobile device management console,"
DECISIONS = ("doc-impact", "no-doc-impact")
KINDS = ("wrong", "missing", "new-page")
# Shorter than this is a word, not a quote.
MIN_QUOTE = 8

SYSTEM = """\
You keep the user manual of {product} true to what it does. You are given a merged \
change and the full text of every page of the manual. Decide whether the change makes \
the manual wrong, or leaves out something new its readers can now use. You do not \
write the changes; a writer does that next.

The change has doc impact only if you can show where, with evidence of one of these kinds:
- wrong: a sentence of a page that the change makes false. Quote that sentence.
- missing: the change adds a new thing a reader operates: a field, button, menu item, \
option, setting, filter, step, command, permission or shortcut. Readers can use it as \
soon as the change is merged, on a screen or in a task a page describes, and the page \
does not mention it. A change that switches a feature flag on makes what the flag hid \
usable, even if the diff shows only the flag; something added behind a flag that stays \
off is not usable yet. Give its label as the change shows it, or the flag line if the \
change only switches it on, and quote the passage of the page it belongs next to.
- new-page: the change adds a screen or a feature, usable as soon as the change is \
merged, that no page covers. Give its label as the change shows it, and say what the \
missing page would describe.
A change to how something the manual already describes behaves is not missing: it has \
doc impact only if it makes a sentence false. If no sentence becomes false and nothing \
new to operate is missing, the change has no doc impact, even when someone using the \
product could notice it.

Rules:
- A change nobody using the product can notice has no doc impact: refactoring, \
renaming inside the code, tests, logging, performance, internal protocol details.
- A page marked "already edited in this merge request" was updated by the change's \
author. The change still has doc impact if the author missed something.
- Judge from the change itself. Do not assume behaviour it does not show.

Finish by calling submit_triage once. In reason, say in one or two sentences what the \
change does for a user, or that it does nothing a user notices. For doc-impact, give \
at least one piece of evidence. Name each page as the manual does after "Page", and \
copy each quote character for character from it: a page or quote that is not in the \
manual is refused."""

SUBMIT = Tool(
    "submit_triage",
    "Submit whether the change affects the manual, with the evidence.",
    {"type": "object",
     "properties": {
         "decision": {"type": "string", "enum": list(DECISIONS)},
         "reason": {"type": "string", "description": "What the change does for a user, or that it does nothing a user notices."},
         "evidence": {"type": "array", "description": "For doc-impact; empty for no-doc-impact.", "items": {
             "type": "object",
             "properties": {
                 "kind": {"type": "string", "enum": list(KINDS)},
                 "page": {"type": "string", "description": "wrong and missing: the page, as the manual names it."},
                 "quote": {"type": "string", "description": "wrong and missing: copied from the page."},
                 "label": {"type": "string", "description": "missing and new-page: the new thing's label, as the change shows it."},
                 "why": {"type": "string", "description": "What the change makes false, what the reader can now use, or what the new page would describe."}},
             "required": ["kind", "why"]}}},
     "required": ["decision", "reason", "evidence"]},
)


def triage(llm: LLM, mr: dict, diffs: list[dict], manual: Manual, edited: list[str], sha: str,
           product: str = PRODUCT) -> dict:
    """Run the triage conversation. `edited` names the pages the merge request edited itself."""
    system, task = SYSTEM.format(product=product), _task(mr, diffs, manual, edited)
    conversation = llm.conversation(system, task, [SUBMIT], cache_key=f"docbot-{sha[:12]}-triage")
    run = agent.run(conversation, {}, SUBMIT.name, lambda answer: validate(answer, manual))
    result = {"schema": SCHEMA, "model": llm.name, "outcome": run["outcome"]}
    if run["outcome"] == "submitted":
        result["answer"] = run["submission"]
    else:
        result["reason"] = run["reason"]
    return {**result, "system": system, "task": task, "turns": run["turns"]}


def validate(answer: dict, manual: Manual) -> str | None:
    """None if the answer can be acted on and its quotes are in the manual, else what is wrong with it."""
    if answer.get("decision") not in DECISIONS:
        return f"decision must be one of {', '.join(DECISIONS)}"
    if not isinstance(answer.get("reason"), str) or not answer["reason"].strip():
        return "'reason' must say why"
    evidence = answer.get("evidence", [])
    if not isinstance(evidence, list):
        return "'evidence' must be a list"
    for n, item in enumerate(evidence, 1):
        if not isinstance(item, dict) or item.get("kind") not in KINDS:
            return f"evidence {n}: kind must be one of {', '.join(KINDS)}"
        if item["kind"] == "new-page":
            continue
        page, quote = item.get("page"), item.get("quote")
        if not isinstance(page, str) or not isinstance(quote, str):
            return f"evidence {n}: {item['kind']} needs 'page' and 'quote'"
        try:
            name = manual.resolve(page)
        except ToolError as e:
            return f"evidence {n}: {e}"
        if len(_squash(quote)) < MIN_QUOTE:
            return f"evidence {n}: quote at least a phrase of the page, not {quote!r}"
        if _squash(quote) not in _squash(manual.pages[name]):
            return f"evidence {n}: {name} does not contain {quote!r}. Copy the quote character for character"
    return None


def _task(mr: dict, diffs: list[dict], manual: Manual, edited: list[str]) -> str:
    # The manual first: it is the same for every merge at one manual version.
    return "\n".join(["# The manual", "", manual.text(edited), *change.describe(mr, diffs),
                      "Call submit_triage when you have decided."])


def _squash(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()
