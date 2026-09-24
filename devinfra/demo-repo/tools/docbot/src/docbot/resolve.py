"""Which merge request produced a commit? Ported from the shell stub.

The answer is derived from repository state rather than from whatever started
the build, so a forced rebuild, a replay and a re-index all resolve to the
same merge request, and a direct push to main resolves to none.
"""

import subprocess


def head_sha() -> str:
    return subprocess.run(["git", "rev-parse", "HEAD"], check=True, capture_output=True, text=True).stdout.strip()


def select_merge(merge_requests: list[dict], sha: str, target_branch: str) -> dict | None:
    """The merge request whose merge or squash commit *is* sha.

    GitLab also lists merge requests that merely contain the commit, so the
    match has to be exact.
    """
    for mr in merge_requests:
        if (mr["state"] == "merged" and mr["target_branch"] == target_branch
                and sha in (mr.get("merge_commit_sha"), mr.get("squash_commit_sha"))):
            return mr
    return None


def resolve(gitlab, sha: str, target_branch: str) -> dict | None:
    return select_merge(gitlab.merge_requests_for_commit(sha) or [], sha, target_branch)
