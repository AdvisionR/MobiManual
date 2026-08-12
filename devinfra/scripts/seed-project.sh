#!/usr/bin/env bash
# Create the demo GitLab project, push the fixture repo, register the webhook,
# and create the Jenkins multibranch job that discovers merge requests.
#
# Idempotent: deletes and recreates the project, so it is safe to re-run to get
# back to a known-good state.
set -euo pipefail
cd "$(dirname "$0")/.."

# shellcheck disable=SC1091
set -a; source .env; source .runtime/gitlab.env; set +a

API="http://${GITLAB_HOST}/api/v4"
PROJECT_PATH="root/mobivisor-console"
PROJECT_ENC="root%2Fmobivisor-console"
JOB_NAME="docbot-mr-probe"
HOOK_URL="http://${JENKINS_HOST}:${JENKINS_PORT}/gitlab-webhook/post"

say() { printf '\n\033[1;36m==>\033[0m %s\n' "$*"; }
ok()  { printf '    \033[0;32mok\033[0m  %s\n' "$*"; }

gl() { curl -s -H "PRIVATE-TOKEN: ${GITLAB_PAT}" "$@"; }

say "Recreating GitLab project ${PROJECT_PATH}"
EXISTING=$(gl "$API/projects/$PROJECT_ENC" | python3 -c 'import sys,json;print(json.load(sys.stdin).get("id",""))' 2>/dev/null || true)
if [ -n "$EXISTING" ]; then
  gl -X DELETE "$API/projects/$EXISTING" >/dev/null
  # GitLab deletes asynchronously; recreating too soon collides with the old path.
  for _ in $(seq 1 30); do
    still=$(gl "$API/projects/$PROJECT_ENC" | python3 -c 'import sys,json;print(json.load(sys.stdin).get("id",""))' 2>/dev/null || true)
    [ -z "$still" ] && break
    sleep 2
  done
  ok "removed previous project (id ${EXISTING})"
fi

gl -X POST --data "name=mobivisor-console&path=mobivisor-console&visibility=private&initialize_with_readme=false" \
   "$API/projects" >/dev/null
ok "project created"

say "Pushing fixture repository"
WORK="$(pwd)/.runtime/seed-repo"
rm -rf "$WORK"; cp -R demo-repo "$WORK"
(
  cd "$WORK"
  git init -q -b main
  git -c user.email=docbot@mobimanual.local -c user.name=DocBot add -A
  git -c user.email=docbot@mobimanual.local -c user.name=DocBot \
      commit -qm "Initial import: console fixture, doc map, DocBot Phase 1 Jenkinsfile"
  git remote add origin "http://root:${GITLAB_PAT}@${GITLAB_HOST}/${PROJECT_PATH}.git"
  git push -q origin main
)
ok "main pushed"

say "Registering webhook -> Jenkins"
# Registered explicitly rather than letting the GitLab Branch Source plugin
# manage it. The plugin's own registration aborts with "No Item credentials
# added, cannot create web hook": its GitLabSCMSource.credentials() resolves to
# null even with a valid credentialsId. The endpoint below is exactly the one
# the plugin would have registered, so runtime behaviour is identical.
for id in $(gl "$API/projects/$PROJECT_ENC/hooks" | python3 -c 'import sys,json;[print(h["id"]) for h in json.load(sys.stdin)]'); do
  gl -X DELETE "$API/projects/$PROJECT_ENC/hooks/$id" >/dev/null
done
gl -X POST --data-urlencode "url=${HOOK_URL}" \
   --data "push_events=true&merge_requests_events=true&note_events=true&enable_ssl_verification=false" \
   "$API/projects/$PROJECT_ENC/hooks" >/dev/null
ok "webhook -> ${HOOK_URL}"

say "Creating Jenkins multibranch job '${JOB_NAME}'"
./scripts/jenkins-groovy.sh - <<GROOVY | sed 's/^/    /'
import jenkins.model.Jenkins
import jenkins.branch.BranchSource
import org.jenkinsci.plugins.workflow.multibranch.WorkflowMultiBranchProject
import io.jenkins.plugins.gitlabbranchsource.GitLabSCMSource
import io.jenkins.plugins.gitlabbranchsource.BranchDiscoveryTrait
import io.jenkins.plugins.gitlabbranchsource.OriginMergeRequestDiscoveryTrait

def j = Jenkins.get()
j.getItem('${JOB_NAME}')?.delete()

def mbp = j.createProject(WorkflowMultiBranchProject, '${JOB_NAME}')
mbp.setDisplayName('DocBot — MR probe')

def src = new GitLabSCMSource('local-gitlab', 'root', '${PROJECT_PATH}')
src.setCredentialsId('gitlab-pat')
src.setTraits([
  new BranchDiscoveryTrait(1),             // branches that are not also MRs
  new OriginMergeRequestDiscoveryTrait(1)  // MRs from this project, merged with target
])
mbp.getSourcesList().add(new BranchSource(src))
mbp.save()
mbp.scheduleBuild2(0)
println "job created, indexing scheduled"
GROOVY
ok "job created"

cat <<EOF

  Project  http://${GITLAB_HOST}/${PROJECT_PATH}
  Job      http://${JENKINS_HOST}:${JENKINS_PORT}/job/${JOB_NAME}/

  Now open a test merge request:
    ./scripts/open-test-mr.sh docs     # touches enrollment code -> expect doc_impact: true
    ./scripts/open-test-mr.sh silent   # touches push transport  -> expect doc_impact: false

EOF
