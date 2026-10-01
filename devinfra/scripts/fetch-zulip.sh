#!/usr/bin/env bash
# Fetch zulip/zulip, the open-source repository DocBot's drafting is evaluated on.
#
#   ./scripts/fetch-zulip.sh
#
# Zulip keeps its user help centre in the repository (starlight_help/) and often
# changes it in the same commit as the code, so its history is a corpus of real
# code changes with the manual edits people actually wrote. zulip/cases.json lists
# the commits used; tools/docbot/tests/test_live_zulip.py replays them.
#
# The clone is bare (DocBot reads git objects, never a working tree), has main
# only, and keeps history since 2026-04-28 only: mistral-medium-3-5 was released
# then, so the model cannot have seen these commits in training. About 60 MB.
# It lives in .runtime/, which is gitignored. Run it again to fetch new commits.
set -euo pipefail
cd "$(dirname "$0")/.."

DEST=.runtime/zulip.git
SINCE=2026-04-28

if [ -d "$DEST" ]; then
  git -C "$DEST" fetch -q --shallow-since="$SINCE" origin main:main
else
  mkdir -p .runtime
  git clone -q --bare --single-branch --branch main --shallow-since="$SINCE" \
    https://github.com/zulip/zulip.git "$DEST"
fi
echo "zulip: $(git -C "$DEST" rev-list --count main) commits since $SINCE in $DEST ($(du -sh "$DEST" | awk '{print $1}'))"
