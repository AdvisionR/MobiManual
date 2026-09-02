#!/usr/bin/env bash
# Open a merge request against the fixture monorepo, and optionally merge it so
# DocBot actually runs.
#
#   ./scripts/open-test-mr.sh [kind] [--merge]
#
# `kind` picks which half of the monorepo the merge request touches, which is
# the only reason the fixture carries both. Each kind maps to a doc-map area
# with a documented expected behaviour — see demo-repo/README.md.
#
#   code      public/app/enrollment/ios/**  ai-drafted     (default)
#   kiosk     public/app/policies/kiosk/**  ai-drafted     — also has a screenshot
#   users     public/app/users/**           ai-drafted
#   devices   public/app/devices/**         ai-drafted     — two pages
#   schema    schema/policies/**            generated      — regenerate, never draft
#   internal  server/protocol/apns/**       no-doc-impact  — the gate must stay silent
#   ci        e2e/**                        no-doc-impact  — the gate must stay silent
#   docs      public/doc/en/**              no-doc-impact  — the manual is the output
#   both      code + its manual page        ai-drafted     — already documented
#   unmapped  a path in no area at all      —              — tier 1 cannot answer
#
# The chain this exercises, end to end:
#
#   push branch -> open MR -> GitLab webhook -> Jenkins discovers MR-<iid>
#     --merge:  -> merge to main -> main build -> Jenkinsfile: when { branch 'main' }
#               -> docbot -> detection.json
set -euo pipefail
cd "$(dirname "$0")/.."

# shellcheck disable=SC1091
set -a; source .env; source .runtime/gitlab.env; set +a

API="http://${GITLAB_HOST}/api/v4"
PROJECT_ENC="root%2Fmobivisor-console"
AUTH="${JENKINS_ADMIN_ID}:${JENKINS_ADMIN_PASSWORD}"
BASE="http://${JENKINS_HOST}:${JENKINS_PORT}"

KIND=code
MERGE=""
for arg in "$@"; do
  case "$arg" in
    --merge) MERGE=1 ;;
    -h|--help) sed -n '2,30p' "$0" | sed 's/^# \{0,1\}//'; exit 0 ;;
    -*) echo "unknown option: $arg" >&2; exit 2 ;;
    *)  KIND="$arg" ;;
  esac
done

case "$KIND" in
  code)     FILES="public/app/enrollment/ios/enrollment-wizard.controller.js"; AREA="enrollment-ios (ai-drafted)" ;;
  kiosk)    FILES="public/app/policies/kiosk/kiosk.controller.js";        AREA="kiosk-modes (ai-drafted)" ;;
  users)    FILES="public/app/users/users.controller.js";                 AREA="users (ai-drafted)" ;;
  devices)  FILES="public/app/devices/devices.controller.js";             AREA="devices (ai-drafted), two pages" ;;
  schema)   FILES="schema/policies/android-restrictions.json";            AREA="policy-schema (generated)" ;;
  internal) FILES="server/protocol/apns/push-transport.js";               AREA="push-transport (no-doc-impact)" ;;
  ci)       FILES="e2e/specs/devices.spec.js";                            AREA="ci-and-tests (no-doc-impact)" ;;
  docs)     FILES="public/doc/en/_users.md";                              AREA="manual-source (no-doc-impact)" ;;
  both)     FILES="public/app/enrollment/ios/enrollment-wizard.controller.js public/doc/en/_enrollment_ios.md"
            AREA="enrollment-ios (ai-drafted), already documented in the same MR" ;;
  unmapped) FILES="public/app/reports/export-schedule.controller.js";     AREA="none — tier 1 cannot answer" ;;
  *) echo "unknown kind: $KIND  (try --help)" >&2; exit 2 ;;
esac

STAMP=$(date +%H%M%S)
BRANCH="feature/${KIND}-${STAMP}"
TITLE="A ${KIND} change the bot should judge (${STAMP})"

gl() { curl -s -H "PRIVATE-TOKEN: ${GITLAB_PAT}" "$@"; }

# Append something harmless in the file's own comment syntax. A stamp rather
# than a real edit: what is being tested is which paths the merge touches, not
# what it says.
touch_file() {
  local f="$1" dir; dir=$(dirname "$f"); mkdir -p "$dir"
  case "$f" in
    *.json) python3 - "$f" "$STAMP" <<'PY'
import json, sys
path, stamp = sys.argv[1], sys.argv[2]
with open(path) as fh: doc = json.load(fh)
doc["_touched"] = f"open-test-mr.sh {stamp}"
with open(path, "w") as fh: json.dump(doc, fh, indent=2); fh.write("\n")
PY
            ;;
    *.md)   printf '\n<!-- %s: touched by open-test-mr.sh -->\n' "$STAMP" >> "$f" ;;
    *.yaml|*.yml) printf '\n# %s: touched by open-test-mr.sh\n' "$STAMP" >> "$f" ;;
    *)      [ -f "$f" ] || printf '// Created by open-test-mr.sh: a path no doc-map area claims.\n' > "$f"
            printf '\n// %s: touched by open-test-mr.sh\n' "$STAMP" >> "$f" ;;
  esac
}

WORK="$(pwd)/.runtime/mr-work"
rm -rf "$WORK"
git clone -q "http://root:${GITLAB_PAT}@${GITLAB_HOST}/root/mobivisor-console.git" "$WORK"
(
  cd "$WORK"
  git checkout -q -b "$BRANCH"
  for f in $FILES; do touch_file "$f"; done
  git -c user.email=docbot@mobimanual.local -c user.name=DocBot add -A
  git -c user.email=docbot@mobimanual.local -c user.name=DocBot commit -qm "$TITLE"
  git push -q origin "$BRANCH"
)

IID=$(curl -s -X POST -H "PRIVATE-TOKEN: ${GITLAB_PAT}" \
  --data-urlencode "source_branch=${BRANCH}" \
  --data-urlencode "target_branch=main" \
  --data-urlencode "title=${TITLE}" \
  "$API/projects/$PROJECT_ENC/merge_requests" \
  | python3 -c 'import sys,json;print(json.load(sys.stdin)["iid"])')

printf '\n  MR !%s opened  (%s)\n' "$IID" "$TITLE"
printf '  touches: %s\n' "$FILES"
printf '  doc-map: %s\n' "$AREA"
printf '  http://%s/root/mobivisor-console/-/merge_requests/%s\n\n' "$GITLAB_HOST" "$IID"

printf '  waiting for Jenkins to discover it'
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
printf '\n  ok  Jenkins discovered MR-%s\n' "$IID"

# The MR build runs with the DocBot stage skipped: the Jenkinsfile guards on
# `branch 'main'`, so nothing happens until the merge request lands.
if [ -z "$MERGE" ]; then
  cat <<EOF

  The DocBot stage does not run on the merge request build — it is guarded on
  main. To see the bot, merge it:

    ./scripts/open-test-mr.sh ${KIND} --merge     # a fresh MR, merged
    or merge !${IID} in the UI and watch ${BASE}/job/docbot/job/main/

EOF
  exit 0
fi

# --- merge, and watch main -------------------------------------------------
# Baseline first: the main build to wait for is the one *after* this number.
BEFORE=$(curl -s -u "$AUTH" "$BASE/job/docbot/job/main/api/json?tree=lastBuild%5Bnumber%5D" \
         | python3 -c 'import sys,json;b=json.load(sys.stdin).get("lastBuild");print(b["number"] if b else 0)')

printf '\n  waiting for GitLab to call it mergeable'
deadline=$((SECONDS + 120))
until [ "$(gl "$API/projects/$PROJECT_ENC/merge_requests/$IID" \
          | python3 -c 'import sys,json;print(json.load(sys.stdin)["merge_status"])')" = "can_be_merged" ]; do
  [ "$SECONDS" -gt "$deadline" ] && { printf '\n  !! MR !%s never became mergeable.\n\n' "$IID"; exit 1; }
  printf '.'; sleep 3
done

MERGE_SHA=$(curl -s -X PUT -H "PRIVATE-TOKEN: ${GITLAB_PAT}" \
  "$API/projects/$PROJECT_ENC/merge_requests/$IID/merge" \
  | python3 -c 'import sys,json;print(json.load(sys.stdin).get("merge_commit_sha") or "")')
[ -n "$MERGE_SHA" ] || { printf '\n  !! merge was refused by GitLab.\n\n'; exit 1; }
printf '\n  ok  merged as %s\n' "${MERGE_SHA:0:8}"

printf '  waiting for the main build'
deadline=$((SECONDS + 300))
NUM=""
until [ -n "$NUM" ]; do
  N=$(curl -s -u "$AUTH" "$BASE/job/docbot/job/main/api/json?tree=lastBuild%5Bnumber,building%5D" \
      | python3 -c 'import sys,json;b=json.load(sys.stdin).get("lastBuild") or {};print("%s %s"%(b.get("number",0),b.get("building")))')
  set -- $N
  if [ "${1:-0}" -gt "$BEFORE" ] && [ "${2:-True}" = "False" ]; then NUM="$1"; break; fi
  [ "$SECONDS" -gt "$deadline" ] && { printf '\n  !! no main build finished within 5 min.\n\n'; exit 1; }
  printf '.'; sleep 5
done
printf '\n  ok  main #%s finished\n\n' "$NUM"

echo "  ---- what the bot saw (detection.json) ----"
if curl -sf -u "$AUTH" "$BASE/job/docbot/job/main/${NUM}/artifact/detection.json" | sed 's/^/  /'; then
  :
else
  echo "  (no artifact — docbot decided there was nothing to do)"
  curl -s -u "$AUTH" "$BASE/job/docbot/job/main/${NUM}/consoleText" | grep -F 'docbot:' | sed 's/^/  /' || true
fi
printf '\n\n  full log: %s/job/docbot/job/main/%s/console\n\n' "$BASE" "$NUM"
