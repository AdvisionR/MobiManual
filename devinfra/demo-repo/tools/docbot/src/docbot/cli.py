"""The command line: arguments, output and exit codes. The decisions live elsewhere.

stdout carries exactly one JSON document, the command's result, so a caller can
redirect it to a file. Everything meant for people goes to stderr.

Exit codes: 0 done, "nothing to do" and "needs a human" included; 1 GitLab or
the model provider unreachable or refusing, or the repository missing a file
DocBot needs; 2 usage or configuration error, raised before any network call.
"""

import json
import subprocess
from enum import Enum
from typing import Annotated, NoReturn

import typer

from docbot import config
from docbot.drafting.repo import Repo, RepoError
from docbot.gitlab import GitLab, GitLabError
from docbot.llm import LLMError
from docbot.llm.mistral import MistralLLM
from docbot.resolve import head_sha
from docbot.update import SCHEMA, update_manual

# Plain tracebacks: they end up in CI logs, not in a terminal.
app = typer.Typer(add_completion=False, no_args_is_help=True, pretty_exceptions_enable=False)


class Context(str, Enum):
    diff = "diff"
    repo = "repo"


@app.callback()
def main() -> None:
    """DocBot: keeps the MobiVisor user manual in step with what merges to main."""


@app.command("update-manual")
def update_manual_command(
    sha: Annotated[str | None, typer.Option(help="Commit on main to process. Default: HEAD of the working directory.")] = None,
    dry_run: Annotated[bool, typer.Option("--dry-run", help="Show the manual change, write nothing.")] = False,
    context: Annotated[Context, typer.Option(
        help="What the drafting model sees: the diff only, or also a search over the code at the merge commit.")] = Context.diff,
    repo_path: Annotated[str | None, typer.Option(
        "--repo", help="A git checkout that contains the merge commit. Needed with --context repo.")] = None,
) -> None:
    """Draft a docs merge request for the merge that produced a commit on main."""
    try:
        settings = config.load()
        llm_settings = config.load_llm()
        sha = sha or head_sha()
    except config.ConfigError as e:
        _usage_error(str(e))
    except (OSError, subprocess.CalledProcessError):
        _usage_error("cannot read HEAD: run inside a git checkout, or pass --sha")

    repo = None
    if context is Context.repo:
        if repo_path is None:
            _usage_error("--context repo needs --repo, a checkout that contains the merge commit")
        try:
            repo = Repo(repo_path, sha)
        except RepoError as e:
            _usage_error(f"{e}; fetch it, or point --repo at a checkout that has it")

    gitlab = GitLab(settings.gitlab_url, settings.project, settings.token)
    llm = MistralLLM(llm_settings.api_key, llm_settings.model)
    try:
        result = update_manual(gitlab, llm, sha, dry_run=dry_run, repo=repo)
    except (GitLabError, LLMError) as e:
        result = {"schema": SCHEMA, "sha": sha, "outcome": "error", "error": str(e)}
    _narrate(result)
    print(json.dumps(result, indent=2))
    if result["outcome"] == "error":
        raise typer.Exit(1)


def _usage_error(message: str) -> NoReturn:
    typer.echo(f"docbot: {message}", err=True)
    raise typer.Exit(2)


def _narrate(result: dict) -> None:
    def say(line: str = "") -> None:
        typer.echo(line, err=True)

    if source := result.get("source"):
        say(f"  source  !{source['iid']}  {source['title']}")
        say(f"          {source['author']}  {source['url']}")
    for step in ("triage", "draft"):
        if step in result:
            say(f"  {step:<7} {_summary(result[step])}")
    outcome = result["outcome"]
    if outcome == "skipped":
        say(f"docbot: {result['sha'][:8]}: {result['reason']}, nothing to do")
    elif outcome == "exists":
        mr = result["docs_merge_request"]
        say(f"docbot: already handled by !{mr['iid']} ({mr['state']})  {mr['url']}")
    elif outcome in ("no-doc-impact", "no-change", "needs-human"):
        say(f"docbot: {outcome}: {result['reason']}. No merge request opened")
    elif outcome == "dry-run":
        say(result["diff"])
        say(f"docbot: dry run, nothing written. Would open {result['branch']} -> main")
    elif outcome == "opened":
        mr = result["docs_merge_request"]
        say(f"docbot: opened !{mr['iid']} from {result['branch']}  {mr['url']}")
    elif outcome == "error":
        say(f"docbot: {result['error']}")


def _summary(step: dict) -> str:
    """One line per conversation: what it decided, and what it cost in turns and tokens."""
    usage = [t["usage"] for t in step["turns"]]
    tokens = (f"{sum(u['input_tokens'] for u in usage)} in ({sum(u['cached_tokens'] for u in usage)} cached), "
              f"{sum(u['output_tokens'] for u in usage)} out")
    if step["outcome"] != "submitted":
        decided = f"stopped: {step['reason']}"
    elif "answer" in step:
        decided = step["answer"]["decision"]
    else:
        decided = ", ".join(f"{p['page']} {p['decision']}" for p in step["proposal"]["pages"])
    return f"{decided}  [{step['model']}, {len(usage)} turns, {tokens}]"
