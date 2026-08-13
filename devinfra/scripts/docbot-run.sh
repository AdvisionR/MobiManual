#!/usr/bin/env bash
# Run the real DocBot pipeline against a merge request in the console project:
#
#   changed files (GitLab API)  ->  docbot gate  ->  docbot propose
#
# Usage:
#   ./scripts/docbot-run.sh 3              # gate with the model, then propose
#   ./scripts/docbot-run.sh 3 --no-model   # tier 1 only, no spend, no network
#   ./scripts/docbot-run.sh 3 --dry-run    # render the proposal, write nothing
#
# This is deliberately the same sequence of commands the Jenkinsfile will run,
# with the same artifacts, so that wiring Jenkins is a transcription rather than
# a redesign. §8.5: no logic in Groovy — everything of consequence happens in
# the CLI, which runs identically here on a laptop.
set -euo pipefail
cd "$(dirname "$0")/.."

# shellcheck disable=SC1091
set -a; source .env; source .runtime/gitlab.env; set +a

IID="${1:-}"
[ -n "$IID" ] || { echo "usage: $0 <merge-request-iid> [--no-model] [--dry-run]" >&2; exit 2; }
shift

GATE_FLAGS=()
PROPOSE_FLAGS=()
for arg in "$@"; do
  case "$arg" in
    --no-model) GATE_FLAGS+=("--no-model") ;;
    --dry-run)  PROPOSE_FLAGS+=("--dry-run") ;;
    *) echo "unknown option: $arg (expected --no-model or --dry-run)" >&2; exit 2 ;;
  esac
done
# Expanded below as `${GATE_FLAGS[@]+"${GATE_FLAGS[@]}"}` rather than plain
# `"${GATE_FLAGS[@]}"`: under `set -u` the bash 3.2 that ships with macOS
# treats an empty array expansion as an unbound variable.

API="http://${GITLAB_HOST}/api/v4"
SOURCE_PROJECT="root/mobivisor-console"
SOURCE_ENC="root%2Fmobivisor-console"
DOCS_PROJECT="root/mobivisor-manual"
DOC_MAP="../docbot/examples/doc-map.yaml"
DOCBOT_DIR="$(cd ../docbot && pwd)"
OUT="$(pwd)/.runtime/docbot/mr-${IID}"

say() { printf '\n\033[1;36m==>\033[0m %s\n' "$*"; }

mkdir -p "$OUT"

say "Collecting merge request !${IID} from GitLab"
# The forge API rather than a local merge-base: §8.4 warns that a multibranch
# job checks out a merge commit over a shallow clone, which makes git-side diff
# computation quietly wrong. This is the same call the Jenkinsfile makes.
curl -sf -H "PRIVATE-TOKEN: ${GITLAB_PAT}" \
  "$API/projects/$SOURCE_ENC/merge_requests/$IID/changes" > "$OUT/mr.json"

python3 - "$OUT/mr.json" "$OUT/changed_files.txt" "$OUT/context.env" <<'PY'
import json, shlex, sys
mr = json.load(open(sys.argv[1]))
with open(sys.argv[2], "w") as fh:
    for path in sorted({c["new_path"] for c in mr.get("changes", [])}):
        fh.write(path + "\n")
# The variables a Jenkins multibranch job would already have in the environment
# as CHANGE_ID, CHANGE_TITLE, CHANGE_AUTHOR, CHANGE_BRANCH, CHANGE_TARGET,
# CHANGE_URL (§8.2). Reconstructed here so the docbot invocation below is
# character-for-character what the Jenkinsfile will run.
with open(sys.argv[3], "w") as fh:
    for key, value in {
        "CHANGE_ID": mr["iid"],
        "CHANGE_TITLE": mr["title"],
        "CHANGE_AUTHOR": mr["author"]["username"],
        "CHANGE_BRANCH": mr["source_branch"],
        "CHANGE_TARGET": mr["target_branch"],
        "CHANGE_URL": mr["web_url"],
    }.items():
        fh.write(f"export {key}={shlex.quote(str(value))}\n")
PY

# shellcheck disable=SC1091
source "$OUT/context.env"
printf '    !%s  %s\n' "$CHANGE_ID" "$CHANGE_TITLE"
sed 's/^/      /' "$OUT/changed_files.txt"

say "docbot gate"
(
  cd "$DOCBOT_DIR"
  uv run docbot gate \
    --changed-files "$OUT/changed_files.txt" \
    --doc-map "$DOC_MAP" \
    --mr "$CHANGE_ID" --title "$CHANGE_TITLE" --author "$CHANGE_AUTHOR" \
    --branch "$CHANGE_BRANCH" --target "$CHANGE_TARGET" --url "$CHANGE_URL" \
    --out "$OUT/verdict.json" ${GATE_FLAGS[@]+"${GATE_FLAGS[@]}"}
) | sed 's/^/    /'

if ! python3 -c "import json,sys; sys.exit(0 if json.load(open('$OUT/verdict.json'))['doc_impact'] else 1)"; then
  say "No doc impact — nothing is proposed."
  echo "    §14.3: the gate's job is mostly to say nothing. This is a result, not a failure."
  exit 0
fi

say "docbot propose"
# FORGE_TOKEN is the name §8.5 binds from the `forge-bot-token` credential in
# Jenkins. Here it is the same local throwaway PAT the rest of the stack uses;
# in production it is a bot account whose write access is the docs repo alone.
(
  cd "$DOCBOT_DIR"
  FORGE_TOKEN="${GITLAB_PAT}" FORGE_URL="http://${GITLAB_HOST}" \
  uv run docbot propose \
    --verdict "$OUT/verdict.json" \
    --docs-project "$DOCS_PROJECT" \
    --source-project "$SOURCE_PROJECT" \
    --doc-map "$DOC_MAP" \
    --comment-source \
    --out "$OUT/proposal.json" ${PROPOSE_FLAGS[@]+"${PROPOSE_FLAGS[@]}"}
) | sed 's/^/    /'

printf '\n    artifacts: %s\n\n' "$OUT"
