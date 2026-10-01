"""The drafting step replayed on zulip/zulip's history. Costs credits, so it only runs when asked:

    DOCBOT_LLM_MODEL=mistral-medium-3-5 uv run --env-file .env pytest -m live -s -k zulip

devinfra/zulip/cases.json lists commits that changed the product and its help
centre together. For each, the model gets the code change and the help pages
the commit edited, as they were before it; what the commit's author wrote on
those pages is the reference. The model never sees the reference: the replay
drafts against a commit with the code change and the old help centre. Each
result goes to devinfra/.runtime/zulip-results/, the reference included.
Skipped until devinfra/scripts/fetch-zulip.sh has run.
"""

import difflib
import json
from pathlib import Path

import pytest
from replay import diffs, git

from docbot import config
from docbot.drafting.proposal import propose
from docbot.drafting.repo import Repo
from docbot.llm.mistral import MistralLLM

DEVINFRA = Path(__file__).resolve().parents[5]
CASES_FILE = DEVINFRA / "zulip" / "cases.json"
SETUP: dict = json.loads(CASES_FILE.read_text()) if CASES_FILE.is_file() else {"cases": []}
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


def unified(old: str, new: str, name: str) -> str:
    return "".join(difflib.unified_diff(old.splitlines(keepends=True), new.splitlines(keepends=True),
                                        fromfile=f"a/{name}", tofile=f"b/{name}"))


@pytest.mark.parametrize("context", ["diff", "repo"])
@pytest.mark.parametrize("case", SETUP["cases"], ids=lambda case: case["commit"][:10])
def test_drafting_replays_a_zulip_commit(tmp_path, case, context):
    settings = config.load_llm()
    head, help_root = case["commit"], SETUP["help"]
    base = git(REPO, "rev-parse", f"{head}^").strip()
    commit = without_help_changes(tmp_path / "index", base, head, help_root)

    changed = [line.split("\t") for line in
               git(REPO, "diff-tree", "-r", "--name-status", base, head, "--", help_root).splitlines()]
    edited = [path for status, path in changed if status == "M"]
    pages = {path.removeprefix(help_root): git(REPO, "show", f"{base}:{path}") for path in edited}
    reference = {path.removeprefix(help_root): git(REPO, "show", f"{head}:{path}") for path in edited}
    mr = {"iid": head[:10], "title": git(REPO, "log", "-1", "--format=%s", head).strip(),
          "description": git(REPO, "log", "-1", "--format=%b", head)}

    result = propose(MistralLLM(settings.api_key, settings.model), mr, diffs(REPO, base, commit), pages, commit,
                     repo=Repo(str(REPO), commit) if context == "repo" else None)

    drafted = result.get("edited", {})
    report = {**result, "case": case,
              "added_by_author": [path.removeprefix(help_root) for status, path in changed if status == "A"],
              "reference": {page: unified(pages[page], reference[page], page) for page in pages},
              "drafted": {page: unified(pages[page], drafted[page], page) for page in drafted}}
    RESULTS.mkdir(parents=True, exist_ok=True)
    (RESULTS / f"{head[:10]}-{context}.json").write_text(json.dumps(report, indent=2))

    decisions = {e["page"]: e["decision"] for e in result.get("proposal", {}).get("pages", [])}
    print(f"\n===== {head[:10]} / {context}: {mr['title']}\n"
          f"author edited {len(pages)} page(s); the model: {decisions or result.get('reason')}")
    for page in pages:
        print(f"--- author, {page}\n{report['reference'][page]}--- model\n{report['drafted'].get(page, '(no edit)')}")
    assert result["outcome"] == "submitted", result.get("reason")
