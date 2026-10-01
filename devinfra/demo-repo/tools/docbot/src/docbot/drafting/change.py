"""The merged change as the model reads it: the merge request's text, then its diff."""


def describe(mr: dict, diffs: list[dict]) -> list[str]:
    """Markdown lines, for the start of a task."""
    lines = [f"# Merge request !{mr['iid']}: {mr['title']}", "", (mr.get("description") or "").strip(), "",
             "# The change", ""]
    for d in diffs:
        path = d["new_path"] if d["old_path"] == d["new_path"] else f"{d['old_path']} -> {d['new_path']}"
        # Four backticks, so a diff of a Markdown file cannot close the fence.
        lines += [f"## {path}", "", "````diff", d["diff"].rstrip("\n") or "(no textual diff)", "````", ""]
    return lines
