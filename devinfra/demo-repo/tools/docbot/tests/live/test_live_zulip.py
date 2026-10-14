"""Drafting replayed on zulip/zulip's history. Costs credits, so it only runs when asked:

    DOCBOT_LLM_MODEL=mistral-large-4-0 DOCBOT_LLM_REASONING_EFFORT=high uv run --env-file .env pytest -m live -s -k zulip

devinfra/zulip/cases.json lists commits that changed the product and its help
centre together, and commits that change nothing a user sees. Each is replayed
the way DocBot runs: the ignore list drops what never calls for a help update,
and drafting decides whether the change has doc impact, finds the help pages to
edit in the whole help centre, with read_page and search_manual, and writes the
pages it lacks. The help centre is the one before the commit; the commit's own
help edits and new pages are the reference, which the model never sees. Each result goes to
devinfra/.runtime/zulip-results/, with the pages the model edited next to the
pages the author edited. Skipped until devinfra/scripts/fetch-zulip.sh has run.
"""

import difflib
import json
from pathlib import Path

import pytest
from replay import diffs, git

from docbot import config
from docbot.drafting import ignore
from docbot.drafting.manual import Manual
from docbot.drafting.proposal import propose
from docbot.drafting.repo import Repo
from docbot.llm.mistral import MistralLLM

DEVINFRA = Path(__file__).resolve().parents[5]
CASES_FILE = DEVINFRA / "zulip" / "cases.json"
SETUP: dict = json.loads(CASES_FILE.read_text()) if CASES_FILE.is_file() else {"cases": [], "negatives": []}
REPO = DEVINFRA / SETUP.get("repository", ".runtime/zulip.git")
RESULTS = DEVINFRA / ".runtime" / "zulip-results"

pytestmark = [pytest.mark.live,
              pytest.mark.skipif(not REPO.is_dir(), reason="run devinfra/scripts/fetch-zulip.sh first")]


def without_help_changes(index: Path, base: str, head: str, help_root: str) -> str:
    """A commit on base with head's change to everything but the help centre, which stays as in base."""
    env = {"GIT_INDEX_FILE": str(index)}
    git(REPO, "read-tree", head, env=env)
    entries = []
    for path in git(REPO, "diff-tree", "-r", "--name-only", base, head, "--", help_root).splitlines():
        # base's entry for the path, or mode 0 to drop a file head added
        entries.append(git(REPO, "ls-tree", base, "--", path) or f"0 {'0' * 40}\t{path}\n")
    git(REPO, "update-index", "--index-info", input="".join(entries), env=env)
    tree = git(REPO, "write-tree", env=env).strip()
    return git(REPO, "commit-tree", tree, "-p", base, "-m", f"{head} without its help changes").strip()


def help_centre(commit: str, help_root: str) -> Manual:
    """Every help page and include at commit, named relative to the help root: pages first, then includes."""
    paths = [p for p in git(REPO, "ls-tree", "-r", "--name-only", commit, "--", help_root).splitlines()
             if p.endswith((".md", ".mdx"))]
    paths.sort(key=lambda p: ("/include/" in p, p))
    return Manual({p.removeprefix(help_root): git(REPO, "show", f"{commit}:{p}") for p in paths})


def unified(old: str, new: str, name: str) -> str:
    return "".join(difflib.unified_diff(old.splitlines(keepends=True), new.splitlines(keepends=True),
                                        fromfile=f"a/{name}", tofile=f"b/{name}"))


def replay(tmp_path: Path, head: str) -> dict:
    settings = config.load_llm()
    llm = MistralLLM(settings.api_key, settings.model, reasoning_effort=settings.reasoning_effort)
    head = git(REPO, "rev-parse", head).strip()
    help_root = SETUP["help"]
    base = git(REPO, "rev-parse", f"{head}^").strip()
    commit = without_help_changes(tmp_path / "index", base, head, help_root)
    manual = help_centre(base, help_root)
    mr = {"iid": head[:10], "title": git(REPO, "log", "-1", "--format=%s", head).strip(),
          "description": git(REPO, "log", "-1", "--format=%b", head)}
    selection = ignore.select({"ignore": [{"code": SETUP["ignore"]}]}, diffs(REPO, base, commit), help_root.rstrip("/"))

    changed = [line.split("\t") for line in
               git(REPO, "diff-tree", "-r", "--name-status", base, head, "--", help_root).splitlines()]
    by_author = [path.removeprefix(help_root) for status, path in changed if status == "M"]
    report: dict = {"commit": head, "title": mr["title"], "model": llm.name,
                    "files": {"sent": [d["new_path"] for d in selection.relevant], "ignored": selection.ignored},
                    "edited_by_author": by_author,
                    "added_by_author": [path.removeprefix(help_root) for status, path in changed if status == "A"],
                    "reference": {page: unified(manual.pages[page], git(REPO, "show", f"{head}:{help_root}{page}"), page)
                                  for page in by_author}}
    if selection.relevant:
        drafted = propose(llm, mr, selection.relevant, manual, [], commit, product=SETUP["product"],
                          page_names=SETUP.get("page_names", ""),
                          repo=Repo(str(REPO), commit))
        report["draft"] = drafted
        edited = drafted.get("edited", {})
        report["drafted"] = {page: unified(manual.pages[page], edited[page], page) for page in edited}
        report["edited_by_model"] = list(edited)
        report["added_by_model"] = [page["page"] for page in drafted.get("new_pages", []) if page["decision"] == "create"]
    RESULTS.mkdir(parents=True, exist_ok=True)
    (RESULTS / f"{head[:10]}.json").write_text(json.dumps(report, indent=2))

    print(f"\n===== {head[:10]}: {mr['title']}\n  doc impact: {doc_impact(report)}"
          f"\n  author edited: {by_author} (added {report['added_by_author']})"
          f"\n  model edited:  {report.get('edited_by_model')} (added {report.get('added_by_model')})")
    return report


def doc_impact(report: dict) -> bool:
    """Whether drafting found the change affects the help centre: a page edited, handed to a human, or missing."""
    proposal = report.get("draft", {}).get("proposal", {})
    return bool(proposal.get("missing_pages")) or any(
        entry["decision"] != "no-change" for entry in proposal.get("pages", []))


@pytest.mark.parametrize("case", SETUP["cases"], ids=lambda case: case["commit"][:10])
def test_a_help_change_is_found_and_drafted(tmp_path, case):
    report = replay(tmp_path, case["commit"])
    assert report["draft"]["outcome"] == "submitted", report["draft"].get("reason")
    assert doc_impact(report)


@pytest.mark.parametrize("case", SETUP.get("negatives", []), ids=lambda case: case["commit"][:10])
def test_a_change_nobody_sees_has_no_doc_impact(tmp_path, case):
    report = replay(tmp_path, case["commit"])
    assert report.get("draft", {}).get("outcome", "submitted") == "submitted", report["draft"].get("reason")
    assert not doc_impact(report)
