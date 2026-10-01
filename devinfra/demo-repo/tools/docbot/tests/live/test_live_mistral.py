"""The drafting step against the real Mistral API. Costs credits, so it only runs when asked:

    DOCBOT_LLM_MODEL=mistral-medium-3-5 uv run --env-file .env pytest -m live -s

Each scenario from devinfra/scenarios is applied, as a commit, to a throwaway
repository built from the fixture, and the model drafts the pages the scenario
expects triage to pick. The full result, every turn included, is printed.
Skipped where devinfra/scenarios is not next to the fixture, as in the seeded
GitLab project.
"""

import json
import shutil
from pathlib import Path

import pytest
from replay import diffs, git

from docbot import config
from docbot.drafting.proposal import propose
from docbot.drafting.repo import Repo
from docbot.llm.mistral import MistralLLM

FIXTURE = Path(__file__).resolve().parents[4]
SCENARIOS = FIXTURE.parent / "scenarios"

# The pages each scenario's Expected line says triage picks. The first one must come back "edit".
PAGES = {
    "kiosk-passcode": ["_policies_kiosk.md"],
    "ios-department": ["_enrollment_ios.md"],
    "devices-filter": ["_devices.md", "_devices_id.md"],
}

pytestmark = [pytest.mark.live,
              pytest.mark.skipif(not SCENARIOS.is_dir(), reason="devinfra/scenarios is not next to the fixture")]


def merged(tmp_path: Path, scenario: str) -> tuple[Path, str, str]:
    """A repository with the fixture as its base commit and the scenario applied on top."""
    checkout = tmp_path / "repo"
    shutil.copytree(FIXTURE, checkout, ignore=shutil.ignore_patterns(
        ".git", ".venv", ".env", "__pycache__", ".pytest_cache", ".ruff_cache", "node_modules"))
    git(checkout, "init", "-q")
    git(checkout, "add", ".")
    git(checkout, "commit", "-q", "-m", "fixture")
    base = git(checkout, "rev-parse", "HEAD").strip()
    git(checkout, "am", "-q", str(SCENARIOS / f"{scenario}.patch"))
    return checkout, base, git(checkout, "rev-parse", "HEAD").strip()


@pytest.mark.parametrize("context", ["diff", "repo"])
@pytest.mark.parametrize("scenario", list(PAGES))
def test_the_model_drafts_the_expected_page(tmp_path, scenario, context):
    settings = config.load_llm()
    checkout, base, head = merged(tmp_path, scenario)
    mr = {"iid": 1, "title": git(checkout, "log", "-1", "--format=%s").strip(),
          "description": git(checkout, "log", "-1", "--format=%b")}
    pages = {name: git(checkout, "show", f"{head}:public/doc/en/{name}") for name in PAGES[scenario]}

    result = propose(MistralLLM(settings.api_key, settings.model), mr, diffs(checkout, base, head), pages, head,
                     repo=Repo(str(checkout), head) if context == "repo" else None)

    print(f"\n===== {scenario} / {context}\n{json.dumps(result, indent=2)}")
    assert result["outcome"] == "submitted", result.get("reason")
    decisions = {entry["page"]: entry["decision"] for entry in result["proposal"]["pages"]}
    assert decisions[PAGES[scenario][0]] == "edit"
