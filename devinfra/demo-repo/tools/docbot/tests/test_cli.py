"""The command line on update-manual's real results: a recorded GitLab and a scripted model behind it."""

import json
import os

import httpx2
import pytest
from fakes import FakeLLM, FakeRepo
from test_update import (
    KIOSK_EDIT,
    LOCATIONS,
    LOCATIONS_LEFT,
    LOCATIONS_PAGE,
    SHA,
    Forge,
    drafted,
    merged,
    written,
)
from typer.testing import CliRunner

from docbot import cli
from docbot.gitlab import GitLab
from docbot.llm import agent

ENV = {"DOCBOT_GITLAB_URL": "http://gl", "DOCBOT_PROJECT": "root/mobivisor-console", "DOCBOT_GITLAB_TOKEN": "token",
       "MISTRAL_API_KEY": "key", "DOCBOT_LLM_MODEL": "model", "DOCBOT_LLM_REASONING_EFFORT": "high"}


def invoke(monkeypatch, forge, llm, *args, env=ENV, checkout=True):
    """update-manual, with the checkout replaced by FakeRepo unless checkout is False."""
    if checkout:
        monkeypatch.setattr(cli, "Repo", lambda path, sha: FakeRepo())
    monkeypatch.setattr(cli, "GitLab", lambda url, project, token: GitLab(
        url, project, token, transport=httpx2.MockTransport(forge.handle)))
    monkeypatch.setattr(cli, "MistralLLM", lambda api_key, model, reasoning_effort: llm)
    return CliRunner(env=env).invoke(cli.app, ["update-manual", "--sha", SHA, *args])


@pytest.mark.parametrize("turns, args, outcome, narrated", [
    ([drafted(KIOSK_EDIT)], [], "opened", ["draft   _policies_kiosk.md edit  [fake/model, 1 turns"]),
    ([drafted(KIOSK_EDIT)], ["--dry-run"], "dry-run", ["draft   _policies_kiosk.md edit", "+++ b/public/doc/en/"]),
    ([drafted(reason="a refactor")], [], "no-doc-impact", ["draft   no page to change", "no-doc-impact: a refactor."]),
    ([drafted(missing=[LOCATIONS]), written(LOCATIONS_LEFT)], [], "needs-human",
     ["draft   _locations.md new: needs-human", "the manual has no _locations.md"]),
    ([drafted(missing=[LOCATIONS]), written(LOCATIONS_PAGE)], ["--dry-run"], "dry-run",
     ["draft   _locations.md new: create", "+++ b/public/doc/en/_locations.md"]),
    ([drafted(reason="") for _ in range(agent.MAX_CALLS)], [], "needs-human", ["draft   stopped: no valid submit_proposal"]),
])
def test_stdout_is_the_result_and_stderr_narrates_each_conversation(monkeypatch, turns, args, outcome, narrated):
    result = invoke(monkeypatch, Forge(commit_mrs=[merged()]), FakeLLM(*turns), *args)
    assert result.exit_code == 0, result.stderr
    assert json.loads(result.stdout)["outcome"] == outcome
    for line in narrated:
        assert line in result.stderr


def test_drafting_searches_the_working_directory_by_default(monkeypatch):
    opened = []

    def checkout(path: str, sha: str):
        opened.append((path, sha))
        return FakeRepo()

    monkeypatch.setattr(cli, "Repo", checkout)
    result = invoke(monkeypatch, Forge(commit_mrs=[merged()]), FakeLLM(drafted(KIOSK_EDIT)), checkout=False)
    assert result.exit_code == 0, result.stderr
    assert opened == [(os.getcwd(), SHA)]


@pytest.mark.parametrize("args", [[], ["--repo", "."]])
def test_a_checkout_drafting_cannot_search_is_a_usage_error_before_any_call(monkeypatch, tmp_path, args):
    monkeypatch.chdir(tmp_path)  # not a checkout, so it has no merge commit
    llm = FakeLLM()
    result = invoke(monkeypatch, Forge(commit_mrs=[merged()]), llm, *args, checkout=False)
    assert result.exit_code == 2
    assert "fetch it, or point --repo at a checkout that has it" in result.stderr
    assert llm.opened == []


def test_a_missing_reasoning_effort_is_a_configuration_error_before_any_call(monkeypatch):
    llm = FakeLLM()
    env = {**ENV, "DOCBOT_LLM_REASONING_EFFORT": ""}  # empty counts as missing, whatever the shell has set
    result = invoke(monkeypatch, Forge(commit_mrs=[merged()]), llm, env=env)
    assert result.exit_code == 2
    assert "missing setting: DOCBOT_LLM_REASONING_EFFORT" in result.stderr
    assert llm.opened == []
