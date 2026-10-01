"""The command line on update-manual's real results: a recorded GitLab and a scripted model behind it."""

import json

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
    result = invoke(monkeypatch, Forge(commit_mrs=[merged()]), FakeLLM(*turns), *args)
    assert result.exit_code == 0, result.stderr
    assert json.loads(result.stdout)["outcome"] == outcome
    for line in narrated:
        assert line in result.stderr
