#!/usr/bin/env bash
# Merge a merge request in the console project, the way a maintainer would.
#
#   ./scripts/merge-test-mr.sh 4
#
# DocBot proposes nothing until this has happened. An open merge request is a
# draft of an intention: its branch is rewritten, its scope changes, and some
# are closed unmerged. The manual should describe what shipped, not what was
# once suggested.
#
# Note that this is also the moment the source stops moving. Everything the
# doc-impact record says about the change is final from here on, which is what
# makes one docs merge request per source merge request an honest summary.
set -euo pipefail
cd "$(dirname "$0")/.."

# shellcheck disable=SC1091
set -a; source .env; source .runtime/gitlab.env; set +a

IID="${1:-}"
[ -n "$IID" ] || { echo "usage: $0 <merge-request-iid>" >&2; exit 2; }

API="http://${GITLAB_HOST}/api/v4"
PROJECT_ENC="root%2Fmobivisor-console"

curl -s -X PUT -H "PRIVATE-TOKEN: ${GITLAB_PAT}" \
  "$API/projects/$PROJECT_ENC/merge_requests/$IID/merge" > /tmp/docbot-merge.json

python3 -c '
import sys, json
iid = sys.argv[1]
d = json.load(open("/tmp/docbot-merge.json"))
if "state" not in d:
    print("\n  merge failed: %s\n" % d.get("message", d))
    raise SystemExit(1)
who = (d.get("merged_by") or {}).get("username", "?")
sha = d.get("merge_commit_sha") or d.get("squash_commit_sha") or "?"
print()
print("  MR !%s state: %s  (merged by %s as %s)" % (iid, d["state"], who, sha[:12]))
print()
print("  Now run:  ./scripts/docbot-run.sh %s" % iid)
print()
' "$IID"
rm -f /tmp/docbot-merge.json
