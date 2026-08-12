#!/usr/bin/env bash
# Open a merge request against the fixture project and report what Jenkins did.
#
#   ./scripts/open-test-mr.sh docs     touches an ai-drafted area  -> doc_impact true
#   ./scripts/open-test-mr.sh silent   touches a no-doc-impact area -> doc_impact false
#
# The second case matters as much as the first: foundation doc §14.3 — "the
# gate's job is mostly to say nothing."
set -euo pipefail
cd "$(dirname "$0")/.."

# shellcheck disable=SC1091
set -a; source .env; source .runtime/gitlab.env; set +a

SCENARIO="${1:-docs}"
API="http://${GITLAB_HOST}/api/v4"
PROJECT_ENC="root%2Fmobivisor-console"
STAMP=$(date +%H%M%S)

case "$SCENARIO" in
  docs)
    BRANCH="feature/enrollment-${STAMP}"
    FILE="src/enrollment/ios/EnrollmentWizard.tsx"
    LINE="// ${STAMP}: wizard copy changed — user-facing, should reach the manual."
    TITLE="Update iOS enrollment wizard copy (${STAMP})"
    EXPECT="doc_impact: true  (area enrollment-ios, class ai-drafted)"
    ;;
  silent)
    BRANCH="chore/push-transport-${STAMP}"
    FILE="src/protocol/apns/PushTransport.ts"
    LINE="// ${STAMP}: retry backoff tuned — internal plumbing, no manual impact."
    TITLE="Tune APNS retry backoff (${STAMP})"
    EXPECT="doc_impact: false (area push-transport, class no-doc-impact)"
    ;;
  *) echo "usage: $0 [docs|silent]" >&2; exit 2 ;;
esac

WORK="$(pwd)/.runtime/mr-work"
rm -rf "$WORK"
git clone -q "http://root:${GITLAB_PAT}@${GITLAB_HOST}/root/mobivisor-console.git" "$WORK"
(
  cd "$WORK"
  git checkout -q -b "$BRANCH"
  printf '\n%s\n' "$LINE" >> "$FILE"
  git -c user.email=docbot@mobimanual.local -c user.name=DocBot commit -qam "$TITLE"
  git push -q origin "$BRANCH"
)

IID=$(curl -s -X POST -H "PRIVATE-TOKEN: ${GITLAB_PAT}" \
  --data-urlencode "source_branch=${BRANCH}" \
  --data-urlencode "target_branch=main" \
  --data-urlencode "title=${TITLE}" \
  --data-urlencode "description=Scenario '${SCENARIO}'. Expected ${EXPECT}" \
  "$API/projects/$PROJECT_ENC/merge_requests" \
  | python3 -c 'import sys,json;print(json.load(sys.stdin)["iid"])')

printf '\n  MR !%s opened  (%s)\n  expected: %s\n' "$IID" "$TITLE" "$EXPECT"
printf '  http://%s/root/mobivisor-console/-/merge_requests/%s\n\n' "$GITLAB_HOST" "$IID"

printf '  waiting for Jenkins to pick it up'
AUTH="${JENKINS_ADMIN_ID}:${JENKINS_ADMIN_PASSWORD}"
BASE="http://${JENKINS_HOST}:${JENKINS_PORT}"
deadline=$((SECONDS + 180))
until curl -sf -u "$AUTH" -o /dev/null "$BASE/job/docbot-mr-probe/job/MR-${IID}/1/api/json" 2>/dev/null; do
  if [ "$SECONDS" -gt "$deadline" ]; then
    printf '\n  !! MR-%s did not appear within 3 min.\n' "$IID"
    printf '     Check the webhook deliveries at:\n'
    printf '     http://%s/root/mobivisor-console/-/hooks\n\n' "$GITLAB_HOST"
    exit 1
  fi
  printf '.'; sleep 5
done
printf '\n'

# wait for the build itself to finish
until [ "$(curl -s -u "$AUTH" "$BASE/job/docbot-mr-probe/job/MR-${IID}/1/api/json" \
          | python3 -c 'import sys,json;print(json.load(sys.stdin).get("building"))')" = "False" ]; do
  sleep 3
done

echo "  ---- verdict.json ----"
curl -s -u "$AUTH" "$BASE/job/docbot-mr-probe/job/MR-${IID}/1/artifact/verdict.json" | sed 's/^/  /'
printf '\n  build: %s/job/docbot-mr-probe/job/MR-%s/1/console\n\n' "$BASE" "$IID"
