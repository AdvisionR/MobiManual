"""The doc-impact gate — foundation doc §6.2, §6.3.

"The gate matters more than the writing. Most merges touch tests, CI, or
internals and must produce nothing. Otherwise you generate noise, burn budget,
and train reviewers to rubber-stamp."

Three tiers, of which this module implements the first two:

  1. path filter against the doc map — pure lookup, costs nothing (docmap.py)
  2. cheap model, structured verdict — only for what survives tier 1
  3. drafting agent — Phase 3, not here

What is deliberately *not* sent to the model
--------------------------------------------
File paths, the MR title and the MR description. Never diffs, never file
contents. §10 flags "diffs from a proprietary MDM codebase will leave the
network" as an open governance risk, and the gate does not need them to decide
whether a change is user-facing. Should that sign-off arrive, adding diff
context is a change here and nowhere else.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

from . import verdictlog
from .config import DEFAULT_MODEL
from .docmap import DocMap, Tier1Result, tier1
from .providers import Provider, ProviderError

SCHEMA = "docbot.verdict/1"

#: Below this, a positive verdict is reported but flagged for a human rather
#: than trusted. Tuned from logged verdicts once there are some (§6.3).
CONFIDENCE_FLOOR = 0.5


@dataclass
class MergeRequest:
    id: str = ""
    title: str = ""
    description: str = ""
    author: str = ""
    branch: str = ""
    target: str = ""
    url: str = ""


SYSTEM_PROMPT = """\
You are the documentation-impact gate for MobiVisor, a Mobile Device Management \
(MDM) platform. You decide whether a merge request changes anything a customer \
would see in the MobiVisor end-user manual.

The manual is procedural: numbered click-paths through the admin console, \
enrollment walkthroughs, policy configuration steps. It does not document \
internal architecture, transport plumbing, test infrastructure, or APIs.

Answer "user_facing": true only if a reader following the manual would now find \
it wrong, incomplete, or misleading. Refactors, dependency bumps, test changes, \
logging, CI and internal protocol work are not user-facing even when large.

Saying "no" is the common and correct answer. A false positive costs a reviewer \
their attention and teaches them to rubber-stamp; prefer silence when unsure and \
say so in "reason".

Respond with JSON only, exactly this shape:
{"user_facing": bool, "areas": [string], "confidence": float, "reason": string}

"areas" must contain only ids from the candidate list you are given, and must be \
empty when user_facing is false. "confidence" is 0.0-1.0. "reason" is one \
sentence, concrete, naming what convinced you.\
"""


def _candidate_lines(doc_map: DocMap, tier1_result: Tier1Result) -> list[str]:
    """Offer the model area ids to choose from.

    When tier 1 already matched doc-relevant areas, those are the candidates.
    When it escalated only because of unmapped files, every area is a candidate
    — the model is being asked to spot a gap in the map.
    """
    hits = tier1_result.doc_relevant_hits
    areas = [h.area for h in hits] if hits else [
        a for a in doc_map.areas if a.klass != "no-doc-impact"
    ]
    lines = []
    for area in areas:
        detail = area.description or ", ".join(area.pages) or "no description"
        lines.append(f"- `{area.id}` ({area.klass}) — {detail}")
    return lines


def build_prompt(doc_map: DocMap, mr: MergeRequest, tier1_result: Tier1Result) -> str:
    parts = ["## Merge request", f"Title: {mr.title or '(none)'}"]
    if mr.description:
        # Truncated: MR descriptions carry stack traces and pasted logs, which
        # cost tokens and add nothing to a user-facing/not decision.
        parts.append(f"Description: {mr.description[:1500]}")

    parts.append("\n## Changed files")
    for hit in tier1_result.hits:
        parts.append(f"[area {hit.area.id} / {hit.area.klass}]")
        parts.extend(f"  {f}" for f in sorted(hit.files))
    if tier1_result.unmapped:
        parts.append("[no doc-map area matches these]")
        parts.extend(f"  {f}" for f in sorted(tier1_result.unmapped))
    if tier1_result.ignored:
        parts.append(f"[ignored as noise: {len(tier1_result.ignored)} file(s)]")

    parts.append("\n## Candidate manual areas")
    parts.extend(_candidate_lines(doc_map, tier1_result))

    if not tier1_result.doc_relevant_hits:
        parts.append(
            "\nNote: no changed file matched a mapped area. Either this change is "
            "internal, or the doc map is missing an entry. Say which."
        )
    return "\n".join(parts)


def _tier2(
    doc_map: DocMap,
    mr: MergeRequest,
    tier1_result: Tier1Result,
    provider: Provider,
    model: str,
) -> dict[str, Any]:
    prompt = build_prompt(doc_map, mr, tier1_result)
    try:
        completion = provider.complete_json(SYSTEM_PROMPT, prompt, model=model)
    except ProviderError as exc:
        # A gate that crashes blocks merges. Degrade to "ask a human" instead.
        return {
            "ran": False,
            "error": str(exc),
            "provider": getattr(provider, "name", "unknown"),
        }

    data = completion.data
    claimed = data.get("areas") or []
    known = set(doc_map.ids)
    areas = [a for a in claimed if a in known]
    hallucinated = [a for a in claimed if a not in known]

    try:
        confidence = float(data.get("confidence", 0.0))
    except (TypeError, ValueError):
        confidence = 0.0

    result = {
        "ran": True,
        "provider": getattr(provider, "name", "unknown"),
        "model": completion.model,
        "user_facing": bool(data.get("user_facing", False)),
        "areas": areas,
        "confidence": max(0.0, min(1.0, confidence)),
        "reason": str(data.get("reason", ""))[:600],
        "usage": completion.usage,
        "latency_ms": completion.latency_ms,
    }
    if hallucinated:
        # Worth logging rather than hiding: it is a signal the candidate list or
        # the prompt needs work.
        result["rejected_areas"] = hallucinated
    return result


def run(
    doc_map: DocMap,
    changed_files: list[str],
    mr: MergeRequest,
    *,
    provider: Provider | None = None,
    model: str = DEFAULT_MODEL,
    use_model: bool = True,
    log_dir: str | None = None,
) -> dict[str, Any]:
    """Run the gate and return the verdict artifact."""
    t1 = tier1(doc_map, changed_files)

    tier2: dict[str, Any] = {"ran": False, "skipped_because": t1.reason}
    if t1.escalate and use_model and provider is not None:
        tier2 = _tier2(doc_map, mr, t1, provider, model)
    elif t1.escalate and not use_model:
        tier2 = {"ran": False, "skipped_because": "tier 2 disabled (--no-model)"}

    # ---- deciding -------------------------------------------------------
    # Deterministic first (§14.2, "deterministic beats probabilistic").
    generated = [h for h in t1.hits if h.area.klass == "generated"]
    human_only = [h for h in t1.hits if h.area.klass == "human-only"]

    notes: list[str] = []
    if not t1.escalate:
        doc_impact = False
    elif generated:
        # A schema change means the generated tables are out of date. That is a
        # fact about the build, not a judgement call — no model needed.
        doc_impact = True
        notes.append("generated area touched: reference tables must be re-rendered")
    elif tier2.get("ran"):
        doc_impact = bool(tier2.get("user_facing"))
    else:
        # Tier 2 could not run on something tier 1 flagged. Stay conservative.
        doc_impact = True
        notes.append("tier 2 unavailable; defaulting to doc_impact for human triage")

    areas = sorted({h.area.id for h in t1.doc_relevant_hits} | set(tier2.get("areas") or []))
    pages = sorted(
        {p for a in areas if (area := doc_map.area(a)) for p in area.pages}
    )

    actions: list[str] = []
    if generated:
        actions.append("render-reference")
    if doc_impact and any(
        (area := doc_map.area(a)) and area.klass == "ai-drafted" for a in areas
    ):
        actions.append("draft")
    if human_only:
        actions.append("human-review")
        notes.append("human-only area touched: the drafting agent must not edit these pages")
    if doc_impact and tier2.get("ran") and tier2.get("confidence", 1.0) < CONFIDENCE_FLOOR:
        actions.append("human-review")
        notes.append(f"low model confidence ({tier2.get('confidence')})")
    if doc_impact and not t1.doc_relevant_hits and tier2.get("areas"):
        notes.append("doc-map gap: model attributed unmapped files to a known area")

    verdict = {
        "schema": SCHEMA,
        "generated_at": verdictlog.utc_now(),
        "merge_request": asdict(mr),
        "changed_files": list(changed_files),
        "doc_map": str(doc_map.source) if doc_map.source else None,
        "tier1": t1.to_dict(),
        "tier2": tier2,
        "tier_reached": 2 if tier2.get("ran") else 1,
        "doc_impact": doc_impact,
        "areas": areas,
        "pages": pages,
        "actions": sorted(set(actions)),
        "notes": notes,
    }

    verdict["log_path"] = str(verdictlog.append(verdict, log_dir))
    return verdict
