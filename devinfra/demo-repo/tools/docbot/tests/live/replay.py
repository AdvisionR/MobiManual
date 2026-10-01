"""Helpers for the live tests, which replay a change from a local git repository."""

import os
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
