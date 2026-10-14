"""update-manual end to end against the real Mistral API, with GitLab replayed from a local repository.

Costs credits, so it only runs when asked:

    DOCBOT_LLM_MODEL=mistral-large-4-0 DOCBOT_LLM_REASONING_EFFORT=high uv run --env-file .env pytest -m live -s -k update

The laptop dry run without the stack: each scenario from devinfra/scenarios, and
each comment kind of open-test-mr.sh, is committed onto the fixture, and
update_manual runs on that commit with dry_run, so drafting decides. GitLab's
answers come from the local repository, so everything but
the HTTP to a real GitLab is exercised. Each result goes to
devinfra/.runtime/docbot-results/, to be recorded against the case's
expectation. Skipped where devinfra/scenarios is not next to the fixture.
"""

import json
from pathlib import Path
from urllib.parse import unquote

import httpx2
import pytest
from replay import apply_patch, diffs, expectations, fixture_repo, git, scenario_patches

from docbot import config
from docbot.drafting.repo import Repo
from docbot.gitlab import GitLab
from docbot.llm.mistral import MistralLLM
from docbot.update import update_manual

FIXTURE = Path(__file__).resolve().parents[4]
DEVINFRA = FIXTURE.parent
SCENARIOS = DEVINFRA / "scenarios"
RESULTS = DEVINFRA / ".runtime" / "docbot-results"
PREFIX = "/api/v4/projects/root%2Fmobivisor-console/"

# What each scenario should end with is stated in its patch (replay.expectations).
PATCHES = scenario_patches(SCENARIOS) if SCENARIOS.is_dir() else {}
SCENARIO_NAMES = sorted(PATCHES)
# open-test-mr.sh's kinds append a comment, so none is worth documenting: ignored, or silent.
KINDS = {
    "code": (["public/app/enrollment/ios/enrollment-wizard.controller.js"], "no-doc-impact"),
    "internal": (["server/protocol/apns/push-transport.js"], "no-doc-impact"),
    "unmapped": (["public/app/reports/export-schedule.controller.js"], "no-doc-impact"),
    "both": (["public/app/enrollment/ios/enrollment-wizard.controller.js", "public/doc/en/_enrollment_ios.md"],
             "no-doc-impact"),
    "ci": (["e2e/specs/devices.spec.js"], "skipped"),
}

pytestmark = [pytest.mark.live,
              pytest.mark.skipif(not SCENARIOS.is_dir(), reason="devinfra/scenarios is not next to the fixture")]


def stamp(checkout: Path, files: list[str], kind: str) -> str:
    """A kind committed the way open-test-mr.sh makes it: a comment appended to each file."""
    for name in files:
        comment = "<!-- 120000: touched by open-test-mr.sh -->" if name.endswith(".md") else \
            "// 120000: touched by open-test-mr.sh"
        with open(checkout / name, "a") as fh:
            fh.write(f"\n{comment}\n")
    git(checkout, "commit", "-q", "-am", f"A {kind} change the bot should judge (120000)")
    return git(checkout, "rev-parse", "HEAD").strip()


class LocalForge:
    """GitLab's answers for one merge request whose merge commit is head, from a local repository. Writes fail."""

    def __init__(self, checkout: Path, base: str, head: str):
        self.checkout, self.head = checkout, head
        self.diffs = diffs(checkout, base, head)
        self.mr = {"iid": 1, "state": "merged", "target_branch": "main", "labels": [],
                   "merge_commit_sha": head, "squash_commit_sha": None,
                   "title": git(checkout, "log", "-1", "--format=%s").strip(),
                   "description": git(checkout, "log", "-1", "--format=%b"),
                   "author": {"username": "dev"}, "web_url": "http://gitlab.invalid/mr/1"}

    def handle(self, request: httpx2.Request) -> httpx2.Response:
        assert request.method == "GET", "a dry run writes nothing"
        path = request.url.raw_path.decode().split("?")[0].removeprefix(PREFIX)
        if path == f"repository/commits/{self.head}/merge_requests":
            return httpx2.Response(200, json=[self.mr])
        if path == "merge_requests/1/diffs":
            return httpx2.Response(200, json=self.diffs)
        if path == "merge_requests":
            return httpx2.Response(200, json=[])
        if path.startswith("repository/files/") and path.endswith("/raw"):
            name = unquote(path.removeprefix("repository/files/").removesuffix("/raw"))
            ref = request.url.params["ref"]
            if git(self.checkout, "ls-tree", "--name-only", ref, "--", name).strip() == name:
                return httpx2.Response(200, text=git(self.checkout, "show", f"{ref}:{name}"))
        return httpx2.Response(404, json={"message": "404 Not Found"})


def dry_run(checkout: Path, base: str, head: str, case: str) -> dict:
    settings = config.load_llm()
    forge = LocalForge(checkout, base, head)
    gitlab = GitLab("http://gitlab.invalid", "root/mobivisor-console", "token",
                    transport=httpx2.MockTransport(forge.handle))
    llm = MistralLLM(settings.api_key, settings.model, reasoning_effort=settings.reasoning_effort)
    result = update_manual(gitlab, llm, head, Repo(str(checkout), head), dry_run=True)
    RESULTS.mkdir(parents=True, exist_ok=True)
    (RESULTS / f"{case}.json").write_text(json.dumps(result, indent=2) + "\n")
    print(f"\n===== {case}: {result['outcome']}\n{result.get('reason') or result.get('diff', '')}")
    return result


def verdict(result: dict, fields: dict[str, str]) -> str | None:
    """None if a dry run ended as a scenario's Expected- lines say (replay.expectations), else how it did not.

    Only the outcome and which pages are edited and created are checked, not what the edits say.
    """
    must, may = set(fields.get("edits", "").split()), set(fields.get("may-edit", "").split())
    creates = set(fields.get("creates", "").split())
    draft = result.get("draft") or {}
    edited = set(draft.get("edited") or {})
    created = {page["page"] for page in draft.get("new_pages") or [] if page["decision"] == "create"}
    # A dry run stops where it would open the docs merge request.
    if result["outcome"] != ("dry-run" if fields["outcome"] == "opened" else fields["outcome"]):
        return f"outcome {result['outcome']}, expected {fields['outcome']}: {result.get('reason')}"
    if not must <= edited <= must | may:
        return f"edited {sorted(edited)}, expected {sorted(must)} (may also: {sorted(may)})"
    if created != creates:
        return f"created {sorted(created)}, expected {sorted(creates)}"
    return None


@pytest.mark.parametrize("scenario", SCENARIO_NAMES)
def test_update_scenario(tmp_path, scenario):
    checkout = tmp_path / "repo"
    base = fixture_repo(FIXTURE, checkout)
    head = apply_patch(checkout, PATCHES[scenario])
    problem = verdict(dry_run(checkout, base, head, scenario), expectations(PATCHES[scenario]))
    assert problem is None, problem


@pytest.mark.parametrize("kind", list(KINDS))
def test_update_kind(tmp_path, kind):
    files, expected = KINDS[kind]
    checkout = tmp_path / "repo"
    base = fixture_repo(FIXTURE, checkout)
    head = stamp(checkout, files, kind)
    result = dry_run(checkout, base, head, f"kind-{kind}")
    assert result["outcome"] == expected, result.get("reason")
