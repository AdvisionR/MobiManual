"""Open a merge request on the docs repository — foundation doc §7, option B.

    B — bot-authored docs PR on merge, linked back to the source PR. The
    destination.

    C — ledger, batched at release. Each merge writes a structured "doc impact
    record" to a pending queue [...] B and C combine: B detects, C writes.

That last sentence is the design this module implements. The gate has decided
the manual is affected; the drafting agent that would write the prose is Phase
3 and does not exist yet. So what lands in the docs repository is the **C
record** — a structured, reviewable statement of what changed and which pages
are in question — delivered through the **B mechanism**, a merge request linked
back to the source one.

That is deliberately not a placeholder. The record is what the eventual
release-time drafting run consumes, and it is useful on its own the moment a
human reads it: it converts "someone should check the manual" from a thing
people remember into a thing with a queue and a reviewer.

What this module will never do
------------------------------
Write to the docs default branch. §7 D (auto-merge to the published manual) is
rejected and §14.1 makes human review mandatory, so every path here ends at an
open merge request with a human in front of it.
"""

from __future__ import annotations

import re
from datetime import datetime, timezone
from typing import Any

import yaml

from . import verdictlog
from .docmap import DocMap
from .forge import FileChange, Forge, ForgeError, MergeRequestRef

SCHEMA = "docbot.proposal/1"
RECORD_SCHEMA = "docbot.doc-impact/1"

#: Ledger location inside the docs repository (§7 C). Pending records are the
#: queue; a release-time drafting run empties it.
DEFAULT_RECORD_DIR = "doc-impact/pending"

#: Every bot branch is namespaced, so a docs maintainer can tell at a glance
#: which branches are theirs and a branch protection rule can be written
#: against a prefix rather than a list.
BRANCH_PREFIX = "docbot"

DEFAULT_LABELS = ("docbot", "doc-impact")


class ProposeError(RuntimeError):
    pass


def _slug(text: str, limit: int = 40) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")
    return slug[:limit].strip("-")


def branch_name(verdict: dict[str, Any]) -> str:
    """Deterministic in the source merge-request id.

    This is what makes re-running the gate safe. A source MR is usually pushed
    to several times, and each push re-runs the gate; without a stable branch
    name every push would open another docs merge request and the reviewer
    would learn to ignore all of them.
    """
    mr = verdict.get("merge_request") or {}
    mr_id = str(mr.get("id") or "").strip()
    if not mr_id:
        raise ProposeError(
            "verdict has no merge_request.id — cannot derive a stable branch "
            "name, and an unstable one opens a new docs MR on every push"
        )
    slug = _slug(str(mr.get("title") or ""))
    return f"{BRANCH_PREFIX}/mr-{mr_id}" + (f"-{slug}" if slug else "")


def record_path(verdict: dict[str, Any], record_dir: str = DEFAULT_RECORD_DIR) -> str:
    mr_id = str((verdict.get("merge_request") or {}).get("id") or "").strip()
    return f"{record_dir.rstrip('/')}/mr-{mr_id}.yaml"


def _page_classes(verdict: dict[str, Any], doc_map: DocMap | None) -> dict[str, str]:
    """page path -> content class (§6.4).

    From the doc map when one is given. Otherwise from the areas tier 1 matched,
    which the verdict carries — enough for the common case, and the pages a
    tier-2-only attribution adds are simply left unclassified rather than
    guessed at.
    """
    classes: dict[str, str] = {}
    if doc_map is not None:
        for area_id in verdict.get("areas") or []:
            area = doc_map.area(area_id)
            if area:
                for page in area.pages:
                    classes[page] = area.klass
    for matched in (verdict.get("tier1") or {}).get("matched_areas") or []:
        for page in matched.get("pages") or []:
            classes.setdefault(page, matched.get("class", ""))
    return classes


def build_record(verdict: dict[str, Any], doc_map: DocMap | None = None,
                 source_project: str = "") -> dict[str, Any]:
    """The doc-impact record — the C-ledger entry that lands in the docs repo."""
    mr = verdict.get("merge_request") or {}
    tier2 = verdict.get("tier2") or {}
    classes = _page_classes(verdict, doc_map)

    return {
        "schema": RECORD_SCHEMA,
        "recorded_at": verdictlog.utc_now(),
        "source": {
            "project": source_project,
            "merge_request": str(mr.get("id") or ""),
            "title": mr.get("title") or "",
            "author": mr.get("author") or "",
            "branch": mr.get("branch") or "",
            "target": mr.get("target") or "",
            "url": mr.get("url") or "",
            "changed_files": list(verdict.get("changed_files") or []),
        },
        "gate": {
            "decided_at": verdict.get("generated_at"),
            "doc_impact": bool(verdict.get("doc_impact")),
            "tier_reached": verdict.get("tier_reached"),
            "tier1_reason": (verdict.get("tier1") or {}).get("reason", ""),
            "provider": tier2.get("provider"),
            "model": tier2.get("model"),
            # What the *model* said, which is not always the verdict: a touched
            # `generated` area makes doc_impact true whatever tier 2 thinks
            # (§14.2), and conflating the two would put words in the model's
            # mouth in the one document a reviewer reads to judge it.
            "model_user_facing": tier2.get("user_facing"),
            "confidence": tier2.get("confidence"),
            "reason": tier2.get("reason", ""),
            "areas": list(verdict.get("areas") or []),
            "actions": list(verdict.get("actions") or []),
            "notes": list(verdict.get("notes") or []),
        },
        "pages": [
            {
                "path": page,
                "class": classes.get(page, "unknown"),
                # Nothing has been drafted: §11 Phase 3. The reviewer decides
                # what happens next, and "no change needed" is a first-class
                # permitted outcome (§6.6).
                "status": "awaiting-review",
            }
            for page in verdict.get("pages") or []
        ],
    }


RECORD_HEADER = f"""\
# Doc-impact record — generated by MobiManual DocBot. Do not edit by hand.
#
# One record per source merge request (foundation doc §7, delivery model C).
# It states what changed in the product and which manual pages that puts in
# question. It is not a draft: no prose has been written, and the gate does not
# claim to know what the pages should say.
#
# Schema: {RECORD_SCHEMA}
"""


def render_record(record: dict[str, Any]) -> str:
    body = yaml.safe_dump(record, sort_keys=False, allow_unicode=True, width=88)
    return RECORD_HEADER + body


def render_title(verdict: dict[str, Any]) -> str:
    mr = verdict.get("merge_request") or {}
    title = str(mr.get("title") or "").strip() or "(untitled merge request)"
    return f"Doc impact: {title} (!{mr.get('id')})"


def render_description(verdict: dict[str, Any], record: dict[str, Any], path: str) -> str:
    """The merge-request body a human actually reads.

    Written for a reviewer who has not seen the source change and does not know
    what DocBot is. It has to answer three questions immediately: why am I
    looking at this, what does the bot claim, and what am I supposed to do.
    """
    mr = verdict.get("merge_request") or {}
    source = record["source"]
    gate = record["gate"]
    link = f"[!{mr.get('id')}]({mr.get('url')})" if mr.get("url") else f"!{mr.get('id')}"
    project = f" in `{source['project']}`" if source["project"] else ""

    lines = [
        f"DocBot opened this because merge request {link}{project} changed something the "
        "manual describes.",
        "",
        f"> {source['title']}",
        "",
        "## Why the gate spoke",
        "",
        f"- **Tier 1 (path filter)** — {gate['tier1_reason']}",
    ]

    if gate.get("model"):
        confidence = gate.get("confidence")
        confidence_text = f"{confidence:.2f}" if isinstance(confidence, (int, float)) else "n/a"
        lines.append(
            f"- **Tier 2 (`{gate['model']}`)** — "
            f"user_facing=`{str(bool(gate.get('model_user_facing'))).lower()}`, "
            f"confidence {confidence_text}: {gate.get('reason') or '(no reason given)'}"
        )
        if not gate.get("model_user_facing"):
            lines.append(
                "- The model said no and this merge request exists anyway: a deterministic "
                "rule overrode it (§14.2). The rule is the one to check, not the model."
            )
    else:
        lines.append("- **Tier 2** — did not run; the decision above is deterministic.")

    for note in gate.get("notes") or []:
        lines.append(f"- ⚠️ {note}")

    lines += ["", "## Pages in question", ""]
    if record["pages"]:
        for page in record["pages"]:
            lines.append(f"- `{page['path']}` — {page['class']}")
    else:
        lines.append(
            "- None. The gate flagged the change but no doc-map area named a page, "
            "which usually means the doc map needs an entry (§6.5)."
        )

    lines += [
        "",
        "## What is in this merge request",
        "",
        f"One file: `{path}`. **No prose has been drafted.** The drafting agent is Phase 3 "
        "(§11); until it exists this merge request is the queue entry, not the change — "
        "delivery model B carrying a model C record (§7).",
        "",
        "## Changed files in the source merge request",
        "",
        "```",
        *(source["changed_files"] or ["(none reported)"]),
        "```",
        "",
        "## For the reviewer",
        "",
        "- [ ] Are the pages above the right ones? If a page is missing or wrong, the fix "
        "belongs in the **doc map**, not here — a stale map is meant to surface as review "
        "friction (§6.5).",
        "- [ ] Does the manual actually need changing? **\"No change needed\" is a "
        "first-class answer** (§6.6): close this merge request and say why, and the record "
        "is the evidence that it was looked at.",
        "- [ ] If it does, edit the pages on this branch — the record travels with them.",
        "",
        "---",
        "",
        "🤖 Generated by DocBot. Nothing here merges itself: §7 rejects auto-publishing "
        "outright, and §14.1 makes human review mandatory. Note that §7 also flags the "
        "risk this becomes ceremony — *without a named human reviewer, B silently "
        "degrades into D* — which is open question #5.",
    ]
    return "\n".join(lines)


def render_source_comment(mr_ref: MergeRequestRef, record: dict[str, Any]) -> str:
    """The advisory comment posted back on the *source* merge request (§7 A)."""
    pages = record["pages"]
    listed = "\n".join(f"- `{page['path']}`" for page in pages) or "- (no pages mapped)"
    verb = "opened" if mr_ref.created else "updated"
    return (
        f"📘 **DocBot** — this change looks user-facing, so the manual is likely affected.\n\n"
        f"{listed}\n\n"
        f"Docs merge request {verb}: {mr_ref.url}\n\n"
        f"If that is wrong, say so there — a false positive is the expensive error here "
        f"(§14.3), and closing it with a reason is how the gate gets tuned."
    )


def run(
    verdict: dict[str, Any],
    forge: Forge | None = None,
    *,
    docs_project: str,
    doc_map: DocMap | None = None,
    source_project: str = "",
    record_dir: str = DEFAULT_RECORD_DIR,
    target_branch: str | None = None,
    labels: list[str] | None = None,
    comment_source: bool = False,
    log_dir: str | None = None,
) -> dict[str, Any]:
    """Open (or update) the docs merge request for one gate verdict.

    `forge` may be None for a silent verdict, and callers are expected to use
    that: most merges produce no doc impact (§14.3), and a silent run should
    not need a forge URL, a token, or any network at all to complete.
    """
    if not verdict.get("doc_impact"):
        # §6.2: "no impact → exit silently". Reaching the forge at all here
        # would be the bug.
        return _result(verdict, status="skipped", reason="verdict has doc_impact: false", log_dir=log_dir)

    if forge is None:
        raise ProposeError("doc_impact is true but no forge was given")

    record = build_record(verdict, doc_map, source_project)
    path = record_path(verdict, record_dir)
    branch = branch_name(verdict)
    target = target_branch or forge.default_branch(docs_project)
    if branch == target:
        raise ProposeError(f"refusing to commit to the docs default branch ({target})")

    existing = forge.find_open_merge_request(docs_project, source_branch=branch)
    mr_id = (verdict.get("merge_request") or {}).get("id")
    message = (
        f"Doc impact record for {source_project or 'source'}!{mr_id}"
        f"\n\n{verdict.get('merge_request', {}).get('title', '')}".rstrip()
    )

    commit = forge.commit(
        docs_project,
        branch=branch,
        start_branch=target,
        message=message,
        changes=[FileChange(path=path, content=render_record(record))],
    )

    title = render_title(verdict)
    description = render_description(verdict, record, path)
    if existing is not None:
        # Rewrite the body rather than leaving the first verdict's reasoning
        # attached to the latest record.
        mr_ref = forge.update_merge_request(
            docs_project, existing.iid, title=title, description=description
        )
    else:
        mr_ref = forge.open_merge_request(
            docs_project,
            source_branch=branch,
            target_branch=target,
            title=title,
            description=description,
            labels=list(labels or DEFAULT_LABELS),
        )

    note_url = ""
    if comment_source:
        if not source_project:
            raise ProposeError("--comment-source needs --source-project")
        try:
            note = forge.comment(source_project, str(mr_id), render_source_comment(mr_ref, record))
            # GitLab's notes API returns no web_url for a merge-request note,
            # so anchor it onto the source MR rather than reporting nothing and
            # leaving the caller unsure whether the comment was posted.
            source_url = str((verdict.get("merge_request") or {}).get("url") or "")
            note_url = note.url or (f"{source_url}#note_{note.id}" if source_url and note.id else "posted")
        except ForgeError as exc:
            # The docs MR exists; failing the whole run over a courtesy comment
            # would make the caller retry and re-open work already done.
            return _result(
                verdict, status="updated" if existing else "created", record=record, path=path,
                branch=branch, target=target, commit=commit, mr=mr_ref, docs_project=docs_project,
                source_project=source_project, warning=f"could not comment on the source MR: {exc}",
                log_dir=log_dir,
            )

    return _result(
        verdict, status="updated" if existing else "created", record=record, path=path,
        branch=branch, target=target, commit=commit, mr=mr_ref, docs_project=docs_project,
        source_project=source_project, note_url=note_url, log_dir=log_dir,
    )


def _result(
    verdict: dict[str, Any],
    *,
    status: str,
    reason: str = "",
    record: dict[str, Any] | None = None,
    path: str = "",
    branch: str = "",
    target: str = "",
    commit: str = "",
    mr: MergeRequestRef | None = None,
    docs_project: str = "",
    source_project: str = "",
    note_url: str = "",
    warning: str = "",
    log_dir: str | None = None,
) -> dict[str, Any]:
    result: dict[str, Any] = {
        "schema": SCHEMA,
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "status": status,
        "source_merge_request": (verdict.get("merge_request") or {}).get("id", ""),
        "source_project": source_project,
        "docs_project": docs_project,
        "doc_impact": bool(verdict.get("doc_impact")),
        "branch": branch,
        "target_branch": target,
        "record_path": path,
        "commit": commit,
        "merge_request": None if mr is None else {
            "iid": mr.iid, "url": mr.url, "title": mr.title, "created": mr.created,
        },
        "pages": [page["path"] for page in (record or {}).get("pages", [])],
        "areas": list(verdict.get("areas") or []),
        "source_comment": note_url,
    }
    if reason:
        result["reason"] = reason
    if warning:
        result["warning"] = warning
    result["log_path"] = str(verdictlog.append(result, log_dir, verdictlog.PROPOSAL_LOG_NAME))
    return result
