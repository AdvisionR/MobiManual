"""The read-only git tools, against a small repository built in the test."""

import subprocess

import pytest

from docbot.drafting import repo as repo_module
from docbot.drafting.repo import Repo, RepoError
from docbot.llm.agent import ToolError


def git(path, *args):
    return subprocess.run(["git", "-C", str(path), *args], check=True, capture_output=True, text=True).stdout.strip()


@pytest.fixture
def checkout(tmp_path):
    (tmp_path / "public/app/kiosk").mkdir(parents=True)
    (tmp_path / "public/app/kiosk/kiosk.controller.js").write_text("// Kiosk\nvar exitPasscode = '';\n")
    (tmp_path / "public/doc/en").mkdir(parents=True)
    (tmp_path / "public/doc/en/_policies_kiosk.md").write_text("# Kiosk Modes\n\nLeaving kiosk mode ...\n")
    (tmp_path / "logo.png").write_bytes(b"\x89PNG\0\0binary")
    (tmp_path / "long.txt").write_text("".join(f"line {n}\n" for n in range(1, 401)))
    git(tmp_path, "init", "-q")
    git(tmp_path, "add", ".")
    git(tmp_path, "-c", "user.name=t", "-c", "user.email=t@t", "commit", "-q", "-m", "base")
    (tmp_path / "untracked.js").write_text("var exitPasscode;\n")  # in the working tree, not the commit
    return tmp_path


@pytest.fixture
def repo(checkout):
    return Repo(str(checkout), git(checkout, "rev-parse", "HEAD"))


def test_a_commit_the_checkout_lacks_is_refused(checkout):
    with pytest.raises(RepoError, match="does not contain commit"):
        Repo(str(checkout), "0" * 40)


def test_list_files_matches_the_whole_path_and_sees_only_the_commit(repo):
    assert repo.list_files("*kiosk*").splitlines() == ["public/app/kiosk/kiosk.controller.js",
                                                        "public/doc/en/_policies_kiosk.md"]
    assert "untracked.js" not in repo.list_files()
    assert repo.list_files("*.py") == "no files match '*.py'"


def test_grep_gives_path_and_line_without_the_sha(repo):
    assert repo.grep("exitpasscode") == "public/app/kiosk/kiosk.controller.js:2:var exitPasscode = '';"
    assert repo.grep("kiosk", "*.md") == "public/doc/en/_policies_kiosk.md:1:# Kiosk Modes\n" \
                                          "public/doc/en/_policies_kiosk.md:3:Leaving kiosk mode ..."
    assert repo.grep("nowhere") == "no matches for 'nowhere'"


def test_grep_reports_a_bad_pattern_as_a_tool_error(repo):
    with pytest.raises(ToolError, match="grep failed"):
        repo.grep("(unclosed")


def test_grep_is_capped(repo, monkeypatch):
    monkeypatch.setattr(repo_module, "MAX_MATCHES", 3)
    lines = repo.grep("^line", "long.txt").splitlines()
    assert lines[:3] == ["long.txt:1:line 1", "long.txt:2:line 2", "long.txt:3:line 3"]
    assert lines[3] == "... 397 more matching lines; narrow the pattern or the path"


def test_read_file_returns_a_range_without_line_numbers(repo):
    assert repo.read_file("long.txt", 10, 12) == "long.txt, lines 10-12 of 400:\nline 10\nline 11\nline 12"


def test_read_file_is_capped(repo, monkeypatch):
    monkeypatch.setattr(repo_module, "MAX_READ_LINES", 50)
    lines = repo.read_file("long.txt", 20).splitlines()
    assert lines[0] == "long.txt, lines 20-69 of 400:"
    assert len(lines) == 51


@pytest.mark.parametrize("path, start, message", [
    ("nope.js", 1, "no file 'nope.js'"),
    ("public/app", 1, "is a directory"),
    ("logo.png", 1, "binary file"),
    ("long.txt", 500, "has only 400 lines"),
    ("untracked.js", 1, "no file"),
])
def test_read_file_errors(repo, path, start, message):
    with pytest.raises(ToolError, match=message):
        repo.read_file(path, start)


def test_tool_handlers_check_argument_types(repo):
    _, handlers = repo.tools()
    assert handlers["grep"]({"pattern": "exitPasscode", "path": "*.js"}).startswith("public/app/kiosk")
    with pytest.raises(ToolError, match="'start' must be an integer"):
        handlers["read_file"]({"path": "long.txt", "start": "10"})
    with pytest.raises(ToolError, match="'pattern' must be a string"):
        handlers["grep"]({})
