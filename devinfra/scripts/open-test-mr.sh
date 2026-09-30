#!/usr/bin/env bash
# Open a merge request against the fixture monorepo, and optionally merge it so
# DocBot actually runs.
#
#   ./scripts/open-test-mr.sh [scenario|kind] [--merge]
#
# A scenario is a real change: scenarios/<name>.patch, with a title and a
# description the way a developer would write them. It is what the model judges,
# and the default is one worth documenting. Each patch states its expected
# outcome below its "---" line, which git am leaves out of the commit message,
# so the expectation never reaches the model. --help lists the scenarios.
# A scenario applies once; after it has merged, re-seed to run it again.
#
# A kind only appends a comment to a file, so it tests which paths a merge
# touches. doc-map.json ignores some kinds outright; for the rest, the right
# answer from the model is always "no page needs changing". See
# demo-repo/README.md.
#
#   code      public/app/enrollment/ios/**  to the model
#   kiosk     public/app/policies/kiosk/**  to the model   — its page has a screenshot
#   users     public/app/users/**           to the model
#   devices   public/app/devices/**         to the model   — two pages
#   schema    schema/policies/**            to the model
#   internal  server/protocol/apns/**       to the model   — which should find no page
#   ci        e2e/**                        ignored        — no model call at all
#   docs      public/doc/en/**              ignored        — the manual is the output
#   both      code + its manual page        to the model   — told the page was already edited
#   unmapped  a controller with no page     to the model   — which should find no page
#
# The chain this exercises, end to end:
#
#   push branch -> open MR -> GitLab webhook -> Jenkins discovers MR-<iid>
#     --merge:  -> merge to main -> main build -> Jenkinsfile: when { branch 'main' }
#               -> docbot -> docs merge request + result.json
set -euo pipefail
cd "$(dirname "$0")/.."

# shellcheck disable=SC1091
set -a; source .env; source .runtime/gitlab.env; set +a

API="http://${GITLAB_HOST}/api/v4"
PROJECT_ENC="root%2Fmobivisor-console"
AUTH="${JENKINS_ADMIN_ID}:${JENKINS_ADMIN_PASSWORD}"
BASE="http://${JENKINS_HOST}:${JENKINS_PORT}"

usage() {
  awk 'NR == 1 { next } /^#/ { sub(/^# ?/, ""); print; next } { exit }' "$0"
  echo
  echo "Scenarios:"
  for p in scenarios/*.patch; do
    printf '  %-16s %s\n' "$(basename "$p" .patch)" "$(sed -n 's/^Expected: \([^.]*\)\..*/\1/p' "$p")"
  done
}

KIND=ios-department
MERGE=""
for arg in "$@"; do
  case "$arg" in
    --merge) MERGE=1 ;;
    -h|--help) usage; exit 0 ;;
    -*) echo "unknown option: $arg" >&2; exit 2 ;;
    *)  KIND="$arg" ;;
  esac
done

PATCH=""
if [ -f "scenarios/${KIND}.patch" ]; then
  PATCH="$(pwd)/scenarios/${KIND}.patch"
  EXPECT=$(sed -n 's/^Expected: //p' "$PATCH")
else case "$KIND" in
  code)     FILES="public/app/enrollment/ios/enrollment-wizard.controller.js"; EXPECT="to the model" ;;
  kiosk)    FILES="public/app/policies/kiosk/kiosk.controller.js";        EXPECT="to the model" ;;
  users)    FILES="public/app/users/users.controller.js";                 EXPECT="to the model" ;;
  devices)  FILES="public/app/devices/devices.controller.js";             EXPECT="to the model (the area has two pages)" ;;
  schema)   FILES="schema/policies/android-restrictions.json";            EXPECT="to the model" ;;
  internal) FILES="server/protocol/apns/push-transport.js";               EXPECT="to the model, which should find no page" ;;
  ci)       FILES="e2e/specs/devices.spec.js";                            EXPECT="ignored by doc-map.json (ci-and-tests)" ;;
  docs)     FILES="public/doc/en/_users.md";                              EXPECT="ignored by doc-map.json (manual-source)" ;;
  both)     FILES="public/app/enrollment/ios/enrollment-wizard.controller.js public/doc/en/_enrollment_ios.md"
            EXPECT="to the model, told the page was already edited" ;;
  unmapped) FILES="public/app/reports/export-schedule.controller.js";     EXPECT="to the model, which should find no page" ;;
  *) echo "unknown scenario or kind: $KIND  (try --help)" >&2; exit 2 ;;
esac fi

STAMP=$(date +%H%M%S)
BRANCH="feature/${KIND}-${STAMP}"
TITLE="A ${KIND} change the bot should judge (${STAMP})"

gl() { curl -s -H "PRIVATE-TOKEN: ${GITLAB_PAT}" "$@"; }

# Append something harmless in the file's own comment syntax. A stamp rather
# than a real edit: what is being tested is which paths the merge touches, not
# what it says.
#
# A missing file is an error, never created: every kind's file exists in
# demo-repo/, so a missing one means GitLab holds an older fixture than
# demo-repo/. Creating it would open a merge request that looks right while the
# gate is judged against the wrong layout.
touch_file() {
  local f="$1"
  if [ ! -f "$f" ]; then
    printf '\n  !! %s is not in the seeded project.\n' "$f" >&2
    printf '     GitLab holds an older fixture than demo-repo/. Re-seed:  ./scripts/seed-project.sh\n\n' >&2
    exit 1
  fi
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
    *)      printf '\n// %s: touched by open-test-mr.sh\n' "$STAMP" >> "$f" ;;
  esac
}

# A scenario is applied with git am, which keeps the patch's own title and
# description, and falls back to a three-way merge when main has moved on since
# the fixture was seeded (comment stamps from earlier kinds, for instance).
apply_scenario() {
  if ! git -c user.email=docbot@mobimanual.local -c user.name=DocBot am -3 -q "$PATCH"; then
    git am --abort
    printf '\n  !! scenario %s does not apply to main. Re-seed:  ./scripts/seed-project.sh\n\n' "$KIND" >&2
    exit 1
  fi
  # An already-applied patch is not an error to git am: it skips it and makes
  # no commit, which would push a branch identical to main.
  if [ "$(git rev-parse HEAD)" = "$(git rev-parse origin/main)" ]; then
    printf '\n  !! scenario %s is already on main. Re-seed to run it again:  ./scripts/seed-project.sh\n\n' "$KIND" >&2
    exit 1
  fi
}

WORK="$(pwd)/.runtime/mr-work"
rm -rf "$WORK"
git clone -q "http://root:${GITLAB_PAT}@${GITLAB_HOST}/root/mobivisor-console.git" "$WORK"
(
  cd "$WORK"
  git checkout -q -b "$BRANCH"
  if [ -n "$PATCH" ]; then
    apply_scenario
  else
    for f in $FILES; do touch_file "$f"; done
    git -c user.email=docbot@mobimanual.local -c user.name=DocBot add -A
    git -c user.email=docbot@mobimanual.local -c user.name=DocBot commit -qm "$TITLE"
  fi
  git push -q origin "$BRANCH"
)
TITLE=$(git -C "$WORK" log -1 --format=%s)
DESCRIPTION=$(git -C "$WORK" log -1 --format=%b)
FILES=$(git -C "$WORK" diff --name-only HEAD~1 HEAD | tr '\n' ' ')

# GitLab processes a push asynchronously, so a merge request created right after
# `git push` can be refused with HTTP 400 because the source branch is not known
# yet. Retry briefly, and show GitLab's own message if it never succeeds rather
# than dying on a missing "iid" key.
IID=""
for _ in $(seq 1 10); do
  RESP=$(curl -s -X POST -H "PRIVATE-TOKEN: ${GITLAB_PAT}" \
    --data-urlencode "source_branch=${BRANCH}" \
    --data-urlencode "target_branch=main" \
    --data-urlencode "title=${TITLE}" \
    --data-urlencode "description=${DESCRIPTION}" \
    "$API/projects/$PROJECT_ENC/merge_requests")
  IID=$(printf '%s' "$RESP" | python3 -c 'import sys,json;print(json.load(sys.stdin).get("iid",""))' 2>/dev/null || true)
  [ -n "$IID" ] && break
  sleep 1
done
if [ -z "$IID" ]; then
  printf '\n  !! GitLab refused to open the merge request for %s:\n     %s\n\n' "$BRANCH" "$RESP" >&2
  exit 1
fi

printf '\n  MR !%s opened  (%s)\n' "$IID" "$TITLE"
printf '  touches: %s\n' "$FILES"
printf '%s\n' "$EXPECT" | fold -s -w 67 | sed '1s/^/  expect:  /; 2,$s/^/           /'
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

echo "  ---- what the bot did (result.json) ----"
if RESULT=$(curl -sf -u "$AUTH" "$BASE/job/docbot/job/main/${NUM}/artifact/result.json"); then
  printf '%s' "$RESULT" | python3 -c '
import sys, json
r = json.load(sys.stdin)
print("  outcome  %s" % r["outcome"])
for key in ("reason", "error"):
    if key in r: print("  %-8s %s" % (key, r[key]))
if "docs_merge_request" in r: print("  docs MR  !%(iid)s  %(url)s" % r["docs_merge_request"])'
else
  echo "  (no result.json — the build failed before docbot wrote one)"
  curl -s -u "$AUTH" "$BASE/job/docbot/job/main/${NUM}/consoleText" | grep -F 'docbot:' | sed 's/^/  /' || true
fi
printf '\n\n  full log: %s/job/docbot/job/main/%s/console\n\n' "$BASE" "$NUM"
