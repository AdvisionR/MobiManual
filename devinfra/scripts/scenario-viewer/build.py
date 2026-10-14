#!/usr/bin/env python3
"""Builds the scenario viewer: one HTML page with every scenario in devinfra/scenarios, its merge
request next to what DocBot did with it in the runs you name.

    python3 scripts/scenario-viewer/build.py <runs.jsonl> [<runs.jsonl> ...] [-o <page.html>]

Run from devinfra/. Each <runs.jsonl> is what an experiment's run.py wrote (one line per run, as
.runtime/experiments/large-4-2026-10-08/compare.py writes them), with each run's full result in
the folder of the same name without .jsonl. A later file wins where two have the same scenario,
mode and run number. A notes.json next to a .jsonl adds a reader's note to a run:
{"<scenario>/<repo|diff>/<run from 0>": "text"}.

The groups are the folders of devinfra/scenarios. Their titles and order are the headings of
devinfra/scenarios/README.md, "### <title> (`<folder>/`)", and the README's tables give each
scenario's "What it tests". A scenario without runs is shown with its merge request only.
The page goes to .runtime/scenario-viewer.html unless -o says otherwise. Standard library only.
"""

import argparse
import json
import re
from pathlib import Path

DEVINFRA = Path(__file__).resolve().parents[2]
SCENARIOS = DEVINFRA / "scenarios"
TEMPLATE = Path(__file__).resolve().parent / "page.html"


def groups_from_folders() -> list[tuple[str, str, list[str]]]:
    titled = re.findall(r"^### (.+) \(`([a-z0-9-]+)/`\)$", (SCENARIOS / "README.md").read_text(), re.M)
    folders = {d.name for d in SCENARIOS.iterdir() if d.is_dir() and any(d.glob("*.patch"))}
    if missing := folders - {f for _, f in titled}:
        raise SystemExit(f"no heading in scenarios/README.md for {sorted(missing)}")
    return [(title, folder, sorted(p.stem for p in (SCENARIOS / folder).glob("*.patch")))
            for title, folder in titled if folder in folders]


def readme_tests() -> dict[str, dict]:
    tests = {}
    for line in (SCENARIOS / "README.md").read_text().splitlines():
        m = re.match(r"\| `([a-z0-9-]+)` \| (?:edit|silent|needs-human) \| (.*?) \| (.*?) \|$", line)
        if m:
            tests[m.group(1)] = {"change": m.group(2), "tests": m.group(3)}
    return tests


def parse_patch(path: Path) -> dict:
    text = path.read_text()
    head, _, rest = text.partition("\n---\n")
    subject = re.search(r"^Subject: \[PATCH\] (.*(?:\n [^\n]+)*)", head, re.M).group(1).replace("\n ", " ")
    body = head.split("\n\n", 1)[1] if "\n\n" in head else ""
    notes, _, diff = rest.partition("\ndiff --git ")
    expected = {}
    for line in notes.splitlines():
        m = re.match(r"^Expected(?:-([a-z-]+))?: (.*)$", line)
        if m:
            expected[m.group(1) or "text"] = m.group(2)
    files = []
    for chunk in re.split(r"(?m)^(?=diff --git )", "diff --git " + diff):
        if not chunk.startswith("diff --git"):
            continue
        name = re.match(r"diff --git a/(\S+) b/(\S+)", chunk).group(2)
        hunks = chunk[chunk.index("@@"):] if "@@" in chunk else ""
        hunks = re.sub(r"\n-- \n[\d.]+\s*$", "\n", hunks).rstrip("\n")
        lines = hunks.splitlines()
        files.append({"path": name, "new": "\nnew file mode" in chunk.split("@@")[0],
                      "add": sum(1 for line in lines if line.startswith("+")),
                      "del": sum(1 for line in lines if line.startswith("-")),
                      "hunks": hunks})
    return {"subject": subject, "body": body.strip(), "expected": expected, "files": files}


def short(value, n: int = 160) -> str:
    s = value if isinstance(value, str) else json.dumps(value, ensure_ascii=False)
    return s if len(s) <= n else s[:n] + "…"


def run(row: dict, result: dict, experiment: str, note: str | None) -> dict:
    out = {
        "experiment": experiment, "model": row.get("model"),
        "context": row["context"], "rep": row["rep"],
        "pass": row["pass"], "outcome": row["outcome"], "expected": row["expected"],
        "edited": row["edited"], "must": row["must"],
        "seconds": row.get("seconds", 0), "cost": row.get("cost", 0),
        "ignored": (result.get("files") or {}).get("ignored", []),
        "triage": None,
        "final_reason": result.get("reason"),
        "note": note,
        "diff": result.get("diff") or "",
    }
    # Runs from before drafting decided alone have a triage conversation in front of it.
    if tri := result.get("triage"):
        answer = tri.get("answer") or {}
        out["triage"] = {"decision": answer.get("decision"), "reason": answer.get("reason") or tri.get("reason"),
                         "evidence": answer.get("evidence") or []}
    draft = result.get("draft")
    if draft:
        proposal = draft.get("proposal") or {}
        calls = [c for t in draft.get("turns", []) for c in t.get("calls", [])]
        out["draft"] = {
            "outcome": draft.get("outcome"),
            "reason": proposal.get("reason"),
            "new_pages": [{"page": p["page"], "decision": p["decision"], "reason": p.get("reason", "")}
                          for p in draft.get("new_pages") or []],
            "pages": [{"page": p["page"], "decision": p["decision"], "reason": p.get("reason", "")}
                      for p in proposal.get("pages", [])],
            "uncertainties": proposal.get("uncertainties") or [],
            "calls": [{"name": c["name"], "args": "" if c["name"] == "submit_proposal" else short(c.get("arguments", {}))}
                      for c in calls],
        }
    return out


def load_runs(jsonls: list[Path]) -> tuple[dict, list[dict]]:
    runs, experiments = {}, []
    for jsonl in jsonls:
        folder, name = jsonl.with_suffix(""), jsonl.parent.name
        notes_file = jsonl.parent / "notes.json"
        notes = json.loads(notes_file.read_text()) if notes_file.is_file() else {}
        rows = [json.loads(line) for line in jsonl.read_text().splitlines() if line.strip()]
        rows = [r for r in rows if not r["case"].startswith("kind-")]
        for row in rows:
            result = json.loads((folder / f"{row['case']}-{row['context']}-{row['rep']}.json").read_text())
            key = (row["case"], row["context"], row["rep"])
            runs[key] = run(row, result, name, notes.get(f"{row['case']}/{row['context']}/{row['rep']}"))
        experiments.append({"name": name, "models": sorted({r.get("model", "?") for r in rows}), "runs": len(rows)})
    return runs, experiments


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("runs", nargs="+", type=Path, help="an experiment's .jsonl")
    ap.add_argument("-o", "--out", type=Path, default=DEVINFRA / ".runtime" / "scenario-viewer.html")
    args = ap.parse_args()

    runs, experiments = load_runs(args.runs)
    tests = readme_tests()
    groups = []
    for title, folder, names in groups_from_folders():
        items = []
        for name in names:
            mine = sorted((r for (case, _, _), r in runs.items() if case == name),
                          key=lambda r: (r["context"] != "repo", r["rep"]))
            items.append({"name": name, **parse_patch(SCENARIOS / folder / f"{name}.patch"),
                          **tests.get(name, {}), "runs": mine})
        groups.append({"title": title, "folder": folder, "scenarios": items})

    data = json.dumps({"groups": groups, "experiments": experiments}, ensure_ascii=False)
    page = TEMPLATE.read_text()
    assert page.count("__DATA__") == 1
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(page.replace("__DATA__", data.replace("</", "<\\/")))
    shown = sum(len(g["scenarios"]) for g in groups)
    with_runs = sum(1 for g in groups for s in g["scenarios"] if s["runs"])
    print(f"{args.out}: {shown} scenarios, {with_runs} with runs, {len(runs)} runs")


if __name__ == "__main__":
    main()
