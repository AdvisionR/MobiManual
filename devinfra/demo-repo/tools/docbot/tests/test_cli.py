"""The command line on update-manual's real results: a recorded GitLab and a scripted model behind it."""

import json
import os

import httpx2
import pytest
from fakes import FakeLLM
from test_update import KIOSK_EDIT, SHA, Forge, drafted, merged, triaged
from typer.testing import CliRunner

from docbot import cli
from docbot.gitlab import GitLab

ENV = {"DOCBOT_GITLAB_URL": "http://gl", "DOCBOT_PROJECT": "root/mobivisor-console", "DOCBOT_GITLAB_TOKEN": "token",
       "MISTRAL_API_KEY": "key", "DOCBOT_LLM_MODEL": "model"}


def invoke(monkeypatch, forge, llm, *args):
    monkeypatch.setattr(cli, "GitLab", lambda url, project, token: GitLab(
        url, project, token, transport=httpx2.MockTransport(forge.handle)))
    monkeypatch.setattr(cli, "MistralLLM", lambda api_key, model: llm)
    return CliRunner(env=ENV).invoke(cli.app, ["update-manual", "--sha", SHA, *args])


@pytest.mark.parametrize("turns, args, outcome, narrated", [
    ([triaged(), drafted(KIOSK_EDIT)], [], "opened", ["triage  doc-impact", "draft   _policies_kiosk.md edit"]),
    ([triaged(), drafted(KIOSK_EDIT)], ["--dry-run"], "dry-run", ["triage  doc-impact", "+++ b/public/doc/en/"]),
    ([triaged(decision="no-doc-impact")], [], "no-doc-impact", ["triage  no-doc-impact"]),
    ([triaged(decision="maybe") for _ in range(20)], [], "needs-human", ["triage  stopped: no valid submit_triage"]),
])
def test_stdout_is_the_result_and_stderr_narrates_each_conversation(monkeypatch, turns, args, outcome, narrated):
    result = invoke(monkeypatch, Forge(commit_mrs=[merged()]), FakeLLM(*turns), "--diff-only", *args)
    assert result.exit_code == 0, result.stderr
    assert json.loads(result.stdout)["outcome"] == outcome
    for line in narrated:
        assert line in result.stderr


def test_drafting_searches_the_working_directory_by_default(monkeypatch):
    opened = []

    class Checkout:
        def __init__(self, path: str, sha: str):
            opened.append((path, sha))

        def tools(self):
            return [], {}

    monkeypatch.setattr(cli, "Repo", Checkout)
    result = invoke(monkeypatch, Forge(commit_mrs=[merged()]), FakeLLM(triaged(), drafted(KIOSK_EDIT)))
    assert result.exit_code == 0, result.stderr
    assert opened == [(os.getcwd(), SHA)]
    assert json.loads(result.stdout)["draft"]["context"] == "repo"


def test_diff_only_drafts_from_the_diff_alone(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)  # not a checkout, so a search would have failed
    result = invoke(monkeypatch, Forge(commit_mrs=[merged()]), FakeLLM(triaged(), drafted(KIOSK_EDIT)), "--diff-only")
    assert result.exit_code == 0, result.stderr
    assert json.loads(result.stdout)["draft"]["context"] == "diff"


@pytest.mark.parametrize("args, message", [
    ([], "or pass --diff-only"),
    (["--repo", "."], "or pass --diff-only"),
    (["--diff-only", "--repo", "."], "--repo has nothing to do"),
])
def test_a_checkout_drafting_cannot_search_is_a_usage_error_before_any_call(monkeypatch, tmp_path, args, message):
    monkeypatch.chdir(tmp_path)  # not a checkout, so it has no merge commit
    llm = FakeLLM()
    result = invoke(monkeypatch, Forge(commit_mrs=[merged()]), llm, *args)
    assert result.exit_code == 2
    assert message in result.stderr
    assert llm.opened == []
