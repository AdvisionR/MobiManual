"""Helpers for the live tests, which replay a change from a local git repository."""

import os
import shutil
import subprocess
from pathlib import Path

# Fixed identity and dates, so a commit the tests create has the same sha on every run.
IDENTITY = {"GIT_AUTHOR_NAME": "docbot", "GIT_AUTHOR_EMAIL": "docbot@localhost",
            "GIT_COMMITTER_NAME": "docbot", "GIT_COMMITTER_EMAIL": "docbot@localhost",
            "GIT_AUTHOR_DATE": "2026-01-01T00:00:00Z", "GIT_COMMITTER_DATE": "2026-01-01T00:00:00Z"}


def git(path: Path | str, *args: str, input: str | None = None, env: dict | None = None) -> str:
    return subprocess.run(["git", "-C", str(path), *args], check=True, capture_output=True, text=True,
                          input=input, env={**os.environ, **IDENTITY, **(env or {})}).stdout


def diffs(repo: Path | str, base: str, head: str) -> list[dict]:
    """The change in the shape of GitLab's /merge_requests/:iid/diffs: hunks only, no file headers."""
    result = []
    for path in git(repo, "diff", "--name-only", base, head).splitlines():
        text = git(repo, "diff", base, head, "--", path)
        result.append({"old_path": path, "new_path": path, "diff": text[text.index("@@"):] if "@@" in text else ""})
    return result


def fixture_repo(fixture: Path, checkout: Path) -> str:
    """A repository at checkout with the fixture as its one commit. Returns that commit."""
    shutil.copytree(fixture, checkout, ignore=shutil.ignore_patterns(
        ".git", ".venv", ".env", "__pycache__", ".pytest_cache", ".ruff_cache", "node_modules"))
    git(checkout, "init", "-q")
    git(checkout, "add", ".")
    git(checkout, "commit", "-q", "-m", "fixture")
    return git(checkout, "rev-parse", "HEAD").strip()


def expectations(patch: Path) -> dict[str, str]:
    """What DocBot should do with a scenario: the Expected-<field> lines below its patch's ---, by field.

    outcome is update-manual's outcome. edits and may-edit name pages, space-separated: the
    ones that must be edited, and the ones that may be as well. outcome-diff-only, where
    present, replaces outcome with --diff-only, and then no page is edited.
    """
    fields = {}
    for line in patch.read_text().split("\ndiff --git", 1)[0].splitlines():
        if line.startswith("Expected-"):
            field, _, value = line.removeprefix("Expected-").partition(": ")
            fields[field] = value
    return fields


def apply_patch(checkout: Path, patch: Path) -> str:
    """A scenario applied the way open-test-mr.sh applies it, as a commit. Returns that commit."""
    git(checkout, "am", "-q", str(patch))
    return git(checkout, "rev-parse", "HEAD").strip()
