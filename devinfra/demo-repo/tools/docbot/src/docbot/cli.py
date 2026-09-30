"""The command line: arguments, output and exit codes. The decisions live elsewhere.

stdout carries exactly one JSON document, the command's result, so a caller can
redirect it to a file. Everything meant for people goes to stderr.

Exit codes: 0 done, "nothing to do" included; 1 GitLab unreachable or refusing;
2 usage or configuration error, raised before any network call.
"""

import json
import subprocess
from typing import Annotated, NoReturn

import typer

from docbot import config
from docbot.gitlab import GitLab, GitLabError
from docbot.resolve import head_sha
from docbot.update import update_manual

# Plain tracebacks: they end up in CI logs, not in a terminal.
app = typer.Typer(add_completion=False, no_args_is_help=True, pretty_exceptions_enable=False)


@app.callback()
def main() -> None:
    """DocBot: keeps the MobiVisor user manual in step with what merges to main."""


@app.command("update-manual")
def update_manual_command(
    sha: Annotated[str | None, typer.Option(help="Commit on main to process. Default: HEAD of the working directory.")] = None,
    dry_run: Annotated[bool, typer.Option("--dry-run", help="Show the manual change, write nothing.")] = False,
) -> None:
    """Open a docs merge request for the merge that last produced a commit on main."""
    try:
        settings = config.load()
        sha = sha or head_sha()
    except config.ConfigError as e:
        _usage_error(str(e))
    except (OSError, subprocess.CalledProcessError):
        _usage_error("cannot read HEAD: run inside a git checkout, or pass --sha")

    gitlab = GitLab(settings.gitlab_url, settings.project, settings.token)
    try:
        result = update_manual(gitlab, sha, dry_run=dry_run)
    except GitLabError as e:
        result = {"schema": "docbot.update/1", "sha": sha, "outcome": "error", "error": str(e)}
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
    outcome = result["outcome"]
    if outcome == "skipped":
        say(f"docbot: {result['sha'][:8]}: {result['reason']}, nothing to do")
    elif outcome == "exists":
        mr = result["docs_merge_request"]
        say(f"docbot: already handled by !{mr['iid']} ({mr['state']})  {mr['url']}")
    elif outcome == "dry-run":
        say(result["diff"])
        say(f"docbot: dry run, nothing written. Would open {result['branch']} -> main")
    elif outcome == "opened":
        mr = result["docs_merge_request"]
        say(f"docbot: opened !{mr['iid']} from {result['branch']}  {mr['url']}")
    elif outcome == "error":
        say(f"docbot: {result['error']}")
