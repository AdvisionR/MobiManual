"""Drafting: a merged merge request in, new manual content out. Pure: no network.

This is a placeholder. It appends the merge request's diff to one fixed file,
which is enough to exercise everything around it: resolving the merge, reading
the manual at the merge commit, committing, and opening the docs merge request.
The drafting agent replaces this module and keeps its signature.
"""

MANUAL_FILE = "public/doc/en/docbot-changes.md"

HEADER = """\
# Changes seen by DocBot

<!-- Placeholder output: DocBot appends one section per merged merge request
     until it edits the real pages instead. Not listed in htmlDocPages, so it
     is not part of the built manual. -->
"""


def draft(current: str | None, mr: dict, diffs: list[dict]) -> str:
    """The new content of MANUAL_FILE. `current` is None if the file does not exist yet."""
    base = HEADER if current is None else current
    return base.rstrip("\n") + "\n\n" + _section(mr, diffs)


def _section(mr: dict, diffs: list[dict]) -> str:
    lines = [f"## !{mr['iid']}: {mr['title']}", "", f"By {mr['author']['username']}: {mr['web_url']}", ""]
    for d in diffs:
        path = d["new_path"] if d["old_path"] == d["new_path"] else f"{d['old_path']} -> {d['new_path']}"
        # Four backticks, so a diff of a Markdown file cannot close the fence.
        lines += [f"### {path}", "", "````diff", d["diff"].rstrip("\n") or "(no textual diff)", "````", ""]
    return "\n".join(lines)
