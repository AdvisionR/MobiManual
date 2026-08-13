#!/usr/bin/env bash
# Create the docs GitLab project and push the fixture manual.
#
# This is the repository DocBot writes to. It is separate from the console
# project on purpose: foundation doc §7 option B is "a bot-authored docs PR,
# linked back to the source PR", and the whole point is that the bot's write
# access is confined to a repository that contains no product code.
#
# Idempotent: deletes and recreates the project, so it is safe to re-run to get
# back to a known-good state. Re-running abandons any docs merge requests that
# were open — they only ever contain generated records, so nothing is lost.
set -euo pipefail
cd "$(dirname "$0")/.."

# shellcheck disable=SC1091
set -a; source .env; source .runtime/gitlab.env; set +a

API="http://${GITLAB_HOST}/api/v4"
PROJECT_PATH="root/mobivisor-manual"
PROJECT_ENC="root%2Fmobivisor-manual"

say() { printf '\n\033[1;36m==>\033[0m %s\n' "$*"; }
ok()  { printf '    \033[0;32mok\033[0m  %s\n' "$*"; }

gl() { curl -s -H "PRIVATE-TOKEN: ${GITLAB_PAT}" "$@"; }
project_id() { gl "$API/projects/$PROJECT_ENC" | python3 -c 'import sys,json;print(json.load(sys.stdin).get("id",""))' 2>/dev/null || true; }

say "Recreating GitLab project ${PROJECT_PATH}"
EXISTING=$(project_id)
if [ -n "$EXISTING" ]; then
  gl -X DELETE "$API/projects/$EXISTING" >/dev/null
  # GitLab deletes asynchronously; recreating too soon collides with the old path.
  for _ in $(seq 1 30); do
    [ -z "$(project_id)" ] && break
    sleep 2
  done
  ok "removed previous project (id ${EXISTING})"
fi

gl -X POST --data "name=mobivisor-manual&path=mobivisor-manual&visibility=private&initialize_with_readme=false" \
   "$API/projects" >/dev/null
ok "project created"

say "Pushing fixture manual"
WORK="$(pwd)/.runtime/docs-seed"
rm -rf "$WORK"; cp -R docs-repo "$WORK"
(
  cd "$WORK"
  git init -q -b main
  git -c user.email=docbot@mobimanual.local -c user.name=DocBot add -A
  git -c user.email=docbot@mobimanual.local -c user.name=DocBot \
      commit -qm "Initial import: manual pages, chapter order, doc-impact ledger"
  git remote add origin "http://root:${GITLAB_PAT}@${GITLAB_HOST}/${PROJECT_PATH}.git"
  git push -q origin main
)
ok "main pushed"

# DocBot only ever opens merge requests here (§14.1: human review is
# mandatory), so make that the rule rather than a convention the bot happens to
# follow. A token that can push to main is a token that can publish to
# customers by accident.
say "Protecting main against direct pushes"
# GitLab protects the default branch on creation, but with
# push_access_level=40 — maintainers, which the bot token is. Replace it.
gl -X DELETE "$API/projects/$PROJECT_ENC/protected_branches/main" >/dev/null 2>&1 || true
gl -X POST --data "name=main&push_access_level=0&merge_access_level=40" \
   "$API/projects/$PROJECT_ENC/protected_branches" >/dev/null
ok "main protected: nobody pushes directly, maintainers may merge"

cat <<EOF

  Docs repo  http://${GITLAB_HOST}/${PROJECT_PATH}
  Ledger     http://${GITLAB_HOST}/${PROJECT_PATH}/-/tree/main/doc-impact/pending

  Now run the gate against a merge request in the console project:
    ./scripts/open-test-mr.sh docs        # opens the source MR
    ./scripts/docbot-run.sh <mr-iid>      # gate + propose -> docs merge request

EOF
