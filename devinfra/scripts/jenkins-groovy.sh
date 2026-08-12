#!/usr/bin/env bash
# Run a Groovy script against the Jenkins script console.
#   ./scripts/jenkins-groovy.sh path/to/script.groovy
#   ./scripts/jenkins-groovy.sh -            # read from stdin
#
# Used instead of Job DSL for job creation: the DSL method names are
# plugin-version specific and fail opaquely, whereas the real classes can be
# introspected and fail loudly.
set -euo pipefail
cd "$(dirname "$0")/.."

# shellcheck disable=SC1091
set -a; source .env; set +a

SRC="${1:?usage: jenkins-groovy.sh <file|->}"
TMP="$(mktemp)"; trap 'rm -f "$TMP" "$TMP.jar"' EXIT
if [ "$SRC" = "-" ]; then cat > "$TMP"; else cat "$SRC" > "$TMP"; fi

AUTH="${JENKINS_ADMIN_ID}:${JENKINS_ADMIN_PASSWORD}"
BASE="http://${JENKINS_HOST}:${JENKINS_PORT}"

CRUMB=$(curl -s -u "$AUTH" -c "$TMP.jar" "$BASE/crumbIssuer/api/json" \
  | python3 -c 'import sys,json;d=json.load(sys.stdin);print(d["crumbRequestField"]+":"+d["crumb"])')

curl -s -u "$AUTH" -b "$TMP.jar" -H "$CRUMB" -X POST \
  --data-urlencode "script@$TMP" "$BASE/scriptText"
