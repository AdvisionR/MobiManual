"""Read-only tools over one commit of a git checkout, for the model to search with.

Every read goes through git objects at the given commit (ls-tree, grep,
cat-file), never the working tree. Untracked files stay invisible, a run can be
repeated from the sha alone, and there is no path to traverse. Results are
capped, so a large repository cannot flood the model's context.
"""

import fnmatch
import subprocess

from docbot.llm import Tool
from docbot.llm.agent import Handler, ToolError, int_arg, str_arg

MAX_FILES = 300
MAX_MATCHES = 50
MAX_LINE_CHARS = 300
MAX_READ_LINES = 500

LIST_FILES = Tool(
    "list_files",
    "List the repository's files at the merge commit whose path matches a glob pattern, "
    f"such as 'public/app/**/*.js' or '*kiosk*'. At most {MAX_FILES} paths.",
    {"type": "object",
     "properties": {"pattern": {"type": "string", "description": "Glob over the whole path. Default '*'."}}},
)
GREP = Tool(
    "grep",
    "Search the files at the merge commit for a regular expression (POSIX extended, case-insensitive). "
    f"Returns 'path:line:text' for at most {MAX_MATCHES} matching lines.",
    {"type": "object",
     "properties": {"pattern": {"type": "string"},
                    "path": {"type": "string", "description": "Glob limiting which files are searched. Default: all."}},
     "required": ["pattern"]},
)
READ_FILE = Tool(
    "read_file",
    f"Read a file at the merge commit, at most {MAX_READ_LINES} lines per call. "
    "Line numbers match grep's. The text is returned without line numbers.",
    {"type": "object",
     "properties": {"path": {"type": "string"},
                    "start": {"type": "integer", "description": "First line, from 1. Default 1."},
                    "end": {"type": "integer", "description": "Last line, inclusive."}},
     "required": ["path"]},
)


class RepoError(Exception):
    """The checkout cannot serve this commit. Raised before any model call."""


class Repo:
    def __init__(self, path: str, sha: str):
        self._path, self._sha = path, sha
        if self._git("cat-file", "-e", f"{sha}^{{commit}}").returncode != 0:
            raise RepoError(f"{path} does not contain commit {sha}")

    def tools(self) -> tuple[list[Tool], dict[str, Handler]]:
        handlers: dict[str, Handler] = {
            "list_files": lambda a: self.list_files(str_arg(a, "pattern", "*")),
            "grep": lambda a: self.grep(str_arg(a, "pattern"), str_arg(a, "path", "")),
            "read_file": lambda a: self.read_file(str_arg(a, "path"), int_arg(a, "start", 1), int_arg(a, "end", 0)),
        }
        return [LIST_FILES, GREP, READ_FILE], handlers

    def list_files(self, pattern: str = "*") -> str:
        paths = self._git("ls-tree", "-r", "--name-only", self._sha).stdout.decode().splitlines()
        matched = [p for p in paths if fnmatch.fnmatch(p, pattern)]
        if not matched:
            return f"no files match {pattern!r}"
        return _capped(matched, MAX_FILES, "paths; narrow the pattern")

    def grep(self, pattern: str, path: str = "") -> str:
        done = self._git("grep", "-n", "-I", "-i", "-E", "-e", pattern, self._sha, "--", *([path] if path else []))
        if done.returncode == 1:
            return f"no matches for {pattern!r}"
        if done.returncode != 0:
            raise ToolError(f"grep failed: {done.stderr.decode().strip()}")
        prefix = f"{self._sha}:"
        lines = [line.removeprefix(prefix)[:MAX_LINE_CHARS] for line in done.stdout.decode(errors="replace").splitlines()]
        return _capped(lines, MAX_MATCHES, "matching lines; narrow the pattern or the path")

    def read_file(self, path: str, start: int = 1, end: int = 0) -> str:
        """Lines start..end, 1-based and inclusive; end 0 means as far as the cap allows."""
        kind = self._git("cat-file", "-t", f"{self._sha}:{path}")
        if kind.returncode != 0:
            raise ToolError(f"no file {path!r} at this commit")
        if kind.stdout.decode().strip() != "blob":
            raise ToolError(f"{path!r} is a directory; use list_files")
        data = self._git("cat-file", "blob", f"{self._sha}:{path}").stdout
        if b"\0" in data:
            raise ToolError(f"{path!r} is a binary file")
        lines = data.decode(errors="replace").splitlines()
        if not lines:
            return f"{path} is empty"
        start = max(start, 1)
        if start > len(lines):
            raise ToolError(f"{path!r} has only {len(lines)} lines")
        end = min(end or len(lines), len(lines), start + MAX_READ_LINES - 1)
        if end < start:
            raise ToolError("end is before start")
        return f"{path}, lines {start}-{end} of {len(lines)}:\n" + "\n".join(lines[start - 1:end])

    def _git(self, *args: str) -> subprocess.CompletedProcess:
        return subprocess.run(["git", "-C", self._path, *args], capture_output=True, check=False)


def _capped(lines: list[str], cap: int, what: str) -> str:
    if len(lines) <= cap:
        return "\n".join(lines)
    return "\n".join(lines[:cap]) + f"\n... {len(lines) - cap} more {what}"

