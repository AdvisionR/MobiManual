"""Offline evaluation — foundation doc §8.6.

"Replay a corpus of historical MRs through `gate` offline and score verdicts
without touching Jenkins."

This is the reason the gate is a library with a CLI on top rather than logic
inside a Jenkinsfile. It is also how §6.3's promise gets cashed: the logged
verdicts become a labelled dataset, and this scores against it.

Corpus format is JSONL, one case per line:

    {"id": "mr-101", "title": "...", "description": "...",
     "changed_files": ["src/..."], "expected_doc_impact": true,
     "expected_areas": ["enrollment-ios"]}
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from . import gate
from .config import DEFAULT_MODEL
from .docmap import DocMap
from .providers import Provider

#: Eval runs log to their own directory. Replay is not production, and mixing
#: the two would poison the dataset §14.4 exists to build. Tests override it
#: again with a tmp path, for the same reason one level down.
EVAL_LOG_DIR = ".docbot/eval"


@dataclass
class CaseResult:
    id: str
    expected: bool
    actual: bool
    expected_areas: list[str]
    actual_areas: list[str]
    tier_reached: int
    reason: str

    @property
    def correct(self) -> bool:
        return self.expected == self.actual

    @property
    def outcome(self) -> str:
        if self.expected and self.actual:
            return "TP"
        if not self.expected and not self.actual:
            return "TN"
        return "FP" if self.actual else "FN"


def load_corpus(path: str | Path) -> list[dict[str, Any]]:
    lines = Path(path).read_text(encoding="utf-8").splitlines()
    return [json.loads(line) for line in lines if line.strip() and not line.startswith("#")]


def run(
    doc_map: DocMap,
    corpus: list[dict[str, Any]],
    *,
    provider: Provider | None = None,
    model: str = DEFAULT_MODEL,
    use_model: bool = True,
    log_dir: str = EVAL_LOG_DIR,
) -> dict[str, Any]:
    results: list[CaseResult] = []

    for case in corpus:
        mr = gate.MergeRequest(
            id=str(case.get("id", "")),
            title=case.get("title", ""),
            description=case.get("description", ""),
        )
        verdict = gate.run(
            doc_map,
            case.get("changed_files", []),
            mr,
            provider=provider,
            model=model,
            use_model=use_model,
            log_dir=log_dir,
        )
        tier2 = verdict["tier2"]
        results.append(
            CaseResult(
                id=mr.id,
                expected=bool(case.get("expected_doc_impact")),
                actual=bool(verdict["doc_impact"]),
                expected_areas=sorted(case.get("expected_areas", [])),
                actual_areas=verdict["areas"],
                tier_reached=verdict["tier_reached"],
                reason=tier2.get("reason") or verdict["tier1"]["reason"],
            )
        )

    tp = sum(1 for r in results if r.outcome == "TP")
    fp = sum(1 for r in results if r.outcome == "FP")
    tn = sum(1 for r in results if r.outcome == "TN")
    fn = sum(1 for r in results if r.outcome == "FN")
    total = len(results) or 1

    precision = tp / (tp + fp) if (tp + fp) else 0.0
    recall = tp / (tp + fn) if (tp + fn) else 0.0
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) else 0.0

    return {
        "schema": "docbot.eval/1",
        "cases": len(results),
        "confusion": {"TP": tp, "FP": fp, "TN": tn, "FN": fn},
        "accuracy": round((tp + tn) / total, 3),
        "precision": round(precision, 3),
        "recall": round(recall, 3),
        "f1": round(f1, 3),
        # §14.3: the gate's job is mostly to say nothing, so a false positive is
        # the expensive error. Tracked separately from accuracy for that reason.
        "false_positive_rate": round(fp / (fp + tn), 3) if (fp + tn) else 0.0,
        "area_exact_match": round(
            sum(1 for r in results if r.actual_areas == r.expected_areas) / total, 3
        ),
        "results": [
            {
                "id": r.id,
                "outcome": r.outcome,
                "expected": r.expected,
                "actual": r.actual,
                "expected_areas": r.expected_areas,
                "actual_areas": r.actual_areas,
                "tier_reached": r.tier_reached,
                "reason": r.reason,
            }
            for r in results
        ],
    }
