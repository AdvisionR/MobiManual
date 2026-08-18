#!/usr/bin/env bash
# Open a merge request against the fixture project and show what the bot did
# with it.
#
#   ./scripts/open-test-mr.sh
#
# The chain this exercises, end to end:
#
#   push branch -> open MR -> GitLab webhook -> Jenkins discovers MR-<iid>
#     -> Jenkinsfile: when { changeRequest() } -> docbot -> detection.json
set -euo pipefail
cd "$(dirname "$0")/.."

# shellcheck disable=SC1091
set -a; source .env; source .runtime/gitlab.env; set +a

API="http://${GITLAB_HOST}/api/v4"
PROJECT_ENC="root%2Fmobivisor-console"
STAMP=$(date +%H%M%S)
BRANCH="feature/change-${STAMP}"
TITLE="A change the bot should notice (${STAMP})"

WORK="$(pwd)/.runtime/mr-work"
rm -rf "$WORK"
git clone -q "http://root:${GITLAB_PAT}@${GITLAB_HOST}/root/mobivisor-console.git" "$WORK"
(
  cd "$WORK"
  git checkout -q -b "$BRANCH"
  printf '\n// %s: touched by open-test-mr.sh\n' "$STAMP" >> src/console.ts
  git -c user.email=docbot@mobimanual.local -c user.name=DocBot commit -qam "$TITLE"
  git push -q origin "$BRANCH"
)

IID=$(curl -s -X POST -H "PRIVATE-TOKEN: ${GITLAB_PAT}" \
  --data-urlencode "source_branch=${BRANCH}" \
  --data-urlencode "target_branch=main" \
  --data-urlencode "title=${TITLE}" \
  "$API/projects/$PROJECT_ENC/merge_requests" \
  | python3 -c 'import sys,json;print(json.load(sys.stdin)["iid"])')

printf '\n  MR !%s opened  (%s)\n' "$IID" "$TITLE"
printf '  http://%s/root/mobivisor-console/-/merge_requests/%s\n\n' "$GITLAB_HOST" "$IID"

printf '  waiting for Jenkins to pick it up'
AUTH="${JENKINS_ADMIN_ID}:${JENKINS_ADMIN_PASSWORD}"
BASE="http://${JENKINS_HOST}:${JENKINS_PORT}"
deadline=$((SECONDS + 180))
until curl -sf -u "$AUTH" -o /dev/null "$BASE/job/docbot/job/MR-${IID}/1/api/json" 2>/dev/null; do
  if [ "$SECONDS" -gt "$deadline" ]; then
    printf '\n  !! MR-%s did not appear within 3 min.\n' "$IID"
    printf '     Check the webhook deliveries at:\n'
    printf '     http://%s/root/mobivisor-console/-/hooks\n\n' "$GITLAB_HOST"
    exit 1
  fi
  printf '.'; sleep 5
done
printf '\n'

# then wait for the build itself to finish
until [ "$(curl -s -u "$AUTH" "$BASE/job/docbot/job/MR-${IID}/1/api/json" \
          | python3 -c 'import sys,json;print(json.load(sys.stdin).get("building"))')" = "False" ]; do
  sleep 3
done

echo "  ---- what the bot saw (detection.json) ----"
curl -s -u "$AUTH" "$BASE/job/docbot/job/MR-${IID}/1/artifact/detection.json" | sed 's/^/  /'
printf '\n\n  full log: %s/job/docbot/job/MR-%s/1/console\n\n' "$BASE" "$IID"
