"""The drafting step against the real Mistral API. Costs credits, so it only runs when asked:

    DOCBOT_LLM_MODEL=mistral-medium-3-5 uv run --env-file .env pytest -m live -s

Each scenario from devinfra/scenarios is applied, as a commit, to a throwaway
repository built from the fixture, and the model drafts with the whole manual,
as after a triage that found doc impact: it picks the pages itself. The full
result, every turn included, is printed.
Skipped where devinfra/scenarios is not next to the fixture, as in the seeded
GitLab project.
"""

import json
from pathlib import Path

import pytest
from replay import apply_patch, diffs, expectations, fixture_repo, git

from docbot import config
from docbot.drafting.manual import Manual, html_doc_pages
from docbot.drafting.proposal import propose
from docbot.drafting.repo import Repo
from docbot.llm.mistral import MistralLLM

FIXTURE = Path(__file__).resolve().parents[4]
SCENARIOS = FIXTURE.parent / "scenarios"

# The scenarios whose patch names pages that must be edited (replay.expectations). The others have no
# doc impact, and drafting only runs after triage found some.
DRAFTED = [patch.stem for patch in sorted(SCENARIOS.glob("*.patch")) if "edits" in expectations(patch)]

pytestmark = [pytest.mark.live,
              pytest.mark.skipif(not SCENARIOS.is_dir(), reason="devinfra/scenarios is not next to the fixture")]


def merged(tmp_path: Path, scenario: str) -> tuple[Path, str, str]:
    """A repository with the fixture as its base commit and the scenario applied on top."""
    checkout = tmp_path / "repo"
    base = fixture_repo(FIXTURE, checkout)
    return checkout, base, apply_patch(checkout, SCENARIOS / f"{scenario}.patch")


@pytest.mark.parametrize("context", ["diff", "repo"])
@pytest.mark.parametrize("scenario", DRAFTED)
def test_the_model_drafts_the_expected_page(tmp_path, scenario, context):
    settings = config.load_llm()
    checkout, base, head = merged(tmp_path, scenario)
    mr = {"iid": 1, "title": git(checkout, "log", "-1", "--format=%s").strip(),
          "description": git(checkout, "log", "-1", "--format=%b")}
    names = html_doc_pages(git(checkout, "show", f"{head}:gruntfile.js"))
    manual = Manual({name: git(checkout, "show", f"{head}:public/doc/en/{name}") for name in names})

    result = propose(MistralLLM(settings.api_key, settings.model), mr, diffs(checkout, base, head), manual, [], head,
                     repo=Repo(str(checkout), head) if context == "repo" else None)

    print(f"\n===== {scenario} / {context}\n{json.dumps(result, indent=2)}")
    assert result["outcome"] == "submitted", result.get("reason")
    decisions = {entry["page"]: entry["decision"] for entry in result["proposal"]["pages"]}
    fields = expectations(SCENARIOS / f"{scenario}.patch")
    # Where the diff alone cannot say what to write, the pages come back needs-human instead.
    expected = "needs-human" if context == "diff" and fields.get("outcome-diff-only") == "needs-human" else "edit"
    pages = fields["edits"].split()
    assert {page: decisions.get(page) for page in pages} == dict.fromkeys(pages, expected)
