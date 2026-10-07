"""Triage: does a merged change affect the manual at all?

One conversation per merge, before drafting. The model reads the merge
request, its diff and the manual's table of contents, and answers doc-impact
or no-doc-impact, with a reason. Which pages to change is drafting's call, not
triage's. Its only tool is submit_triage; the conversation ends when an answer
validates.
"""

from docbot.drafting import change
from docbot.drafting.manual import Manual
from docbot.llm import LLM, Tool, agent

SCHEMA = "docbot.triage/3"
PRODUCT = "MobiVisor, a mobile device management console,"
DECISIONS = ("doc-impact", "no-doc-impact")

SYSTEM = """\
You keep the user manual of {product} true to what it does. You are given a merged \
change and the manual's table of contents. Decide whether the change makes anything \
in the manual wrong or incomplete. You do not decide which pages to change; a \
writer does that next.

Rules:
- The change has doc impact if a reader of the manual would now see, do or be told \
something different from what it says, or if the change adds something such a \
reader needs: a new field, step, option, filter, setting, rule or shortcut.
- A change nobody using the product can notice has no doc impact: refactoring, \
renaming inside the code, tests, logging, performance, internal protocol details.
- A page marked "already edited in this merge request" was updated by the change's \
author. The change still has doc impact if the author missed something.
- Judge from the change itself. Do not assume behaviour it does not show.

Finish by calling submit_triage once. In reason, say in one or two sentences what \
the change does for a user, or that it does nothing a user notices."""

SUBMIT = Tool(
    "submit_triage",
    "Submit whether the change affects the manual.",
    {"type": "object",
     "properties": {
         "decision": {"type": "string", "enum": list(DECISIONS)},
         "reason": {"type": "string", "description": "What the change does for a user, or that it does nothing a user notices."}},
     "required": ["decision", "reason"]},
)


def triage(llm: LLM, mr: dict, diffs: list[dict], manual: Manual, edited: list[str], sha: str,
           product: str = PRODUCT) -> dict:
    """Run the triage conversation. `edited` names the pages the merge request edited itself."""
    system, task = SYSTEM.format(product=product), _task(mr, diffs, manual, edited)
    conversation = llm.conversation(system, task, [SUBMIT], cache_key=f"docbot-{sha[:12]}-triage")
    run = agent.run(conversation, {}, SUBMIT.name, validate)
    result = {"schema": SCHEMA, "model": llm.name, "outcome": run["outcome"]}
    if run["outcome"] == "submitted":
        result["answer"] = run["submission"]
    else:
        result["reason"] = run["reason"]
    return {**result, "system": system, "task": task, "turns": run["turns"]}


def validate(answer: dict) -> str | None:
    """None if the answer can be acted on, else what is wrong with it."""
    if answer.get("decision") not in DECISIONS:
        return f"decision must be one of {', '.join(DECISIONS)}"
    if not isinstance(answer.get("reason"), str) or not answer["reason"].strip():
        return "'reason' must say why"
    return None


def _task(mr: dict, diffs: list[dict], manual: Manual, edited: list[str]) -> str:
    return "\n".join([*change.describe(mr, diffs),
                      "# The manual", "", "Every page in manual order, with its headings:", "",
                      manual.contents(edited), "",
                      "Call submit_triage when you have decided."])
