"""The drafting step against the real Mistral API. Costs credits, so it only runs when asked:

    DOCBOT_LLM_MODEL=mistral-large-4-0 DOCBOT_LLM_REASONING_EFFORT=high uv run --env-file .env pytest -m live -s

Each scenario from devinfra/scenarios is applied, as a commit, to a throwaway
repository built from the fixture, and the model drafts with the whole manual:
it decides whether any page needs changing, picks the pages itself, and writes
the pages the manual lacks. The full result, every turn included, is printed.
Skipped where devinfra/scenarios is not next to the fixture, as in the seeded
GitLab project.
"""

import json
from pathlib import Path

import pytest
from replay import apply_patch, diffs, expectations, fixture_repo, git, scenario_patches

from docbot import config
from docbot.drafting.manual import Manual, html_doc_pages
from docbot.drafting.proposal import propose
from docbot.drafting.repo import Repo
from docbot.llm.mistral import MistralLLM

FIXTURE = Path(__file__).resolve().parents[4]
SCENARIOS = FIXTURE.parent / "scenarios"

# What each scenario should end with is stated in its patch (replay.expectations).
PATCHES = scenario_patches(SCENARIOS) if SCENARIOS.is_dir() else {}

pytestmark = [pytest.mark.live,
              pytest.mark.skipif(not SCENARIOS.is_dir(), reason="devinfra/scenarios is not next to the fixture")]


def merged(tmp_path: Path, scenario: str) -> tuple[Path, str, str]:
    """A repository with the fixture as its base commit and the scenario applied on top."""
    checkout = tmp_path / "repo"
    base = fixture_repo(FIXTURE, checkout)
    return checkout, base, apply_patch(checkout, PATCHES[scenario])


@pytest.mark.parametrize("context", ["diff", "repo"])
@pytest.mark.parametrize("scenario", sorted(PATCHES))
def test_the_model_drafts_the_expected_pages(tmp_path, scenario, context):
    settings = config.load_llm()
    checkout, base, head = merged(tmp_path, scenario)
    mr = {"iid": 1, "title": git(checkout, "log", "-1", "--format=%s").strip(),
          "description": git(checkout, "log", "-1", "--format=%b")}
    names = html_doc_pages(git(checkout, "show", f"{head}:gruntfile.js"))
    manual = Manual({name: git(checkout, "show", f"{head}:public/doc/en/{name}") for name in names})

    llm = MistralLLM(settings.api_key, settings.model, reasoning_effort=settings.reasoning_effort)
    result = propose(llm, mr, diffs(checkout, base, head), manual, [], head,
                     repo=Repo(str(checkout), head) if context == "repo" else None)

    print(f"\n===== {scenario} / {context}\n{json.dumps(result, indent=2)}")
    assert result["outcome"] == "submitted", result.get("reason")
    proposal = result["proposal"]
    decisions = {entry["page"]: entry["decision"] for entry in proposal["pages"]}
    created = {page["page"] for page in result["new_pages"] if page["decision"] == "create"}
    fields = expectations(PATCHES[scenario])
    diff_only = context == "diff" and "outcome-diff-only" in fields
    outcome = fields["outcome-diff-only"] if diff_only else fields["outcome"]
    if outcome == "no-doc-impact":
        assert set(decisions.values()) <= {"no-change"}, decisions
        assert not proposal["missing_pages"]
        return
    # Where the diff alone cannot say what to write, the pages come back needs-human instead.
    expected = "needs-human" if outcome == "needs-human" else "edit"
    pages = fields.get("edits", "").split()
    assert {page: decisions.get(page) for page in pages} == dict.fromkeys(pages, expected)
    assert created == (set() if diff_only else set(fields.get("creates", "").split()))
