#!/usr/bin/env bash
# Create the GitLab project, push the fixture repo, and create the Jenkins
# multibranch job that discovers merge requests. Jenkins registers the webhook
# itself when the job's SCM source is saved; this script verifies that it did.
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
JOB_NAME="docbot"

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
      commit -qm "Initial import: console fixture and DocBot Jenkinsfile"
  git remote add origin "http://root:${GITLAB_PAT}@${GITLAB_HOST}/${PROJECT_PATH}.git"
  git push -q origin main
)
ok "main pushed"

say "Creating Jenkins multibranch job '${JOB_NAME}'"
# The webhook is NOT registered here. Jenkins does it, on save of the SCM
# source below, because casc/jenkins.yaml sets manageWebHooks: true. 
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
mbp.setDisplayName('DocBot')

def src = new GitLabSCMSource('local-gitlab', 'root', '${PROJECT_PATH}')
src.setCredentialsId('gitlab-pat')
src.setTraits([
  new BranchDiscoveryTrait(1),             // branches that are not also MRs
  new OriginMergeRequestDiscoveryTrait(1)  // MRs from this project, merged with target
])
mbp.getSourcesList().add(new BranchSource(src))
mbp.save()

// Registers the GitLab webhook. Needed because this job is built
// programmatically: SCMSource.afterSave() is what triggers hook registration,
// and branch-api only calls it from the UI's form-submit path —
// WorkflowMultiBranchProject has no afterSave() of its own, so mbp.save() does
// not reach the sources. Read back from the project rather than reusing the
// local \`src\`, so the source's owner is set and GitLabServer.getCredentials()
// has an item to resolve against.
mbp.SCMSources.each { it.afterSave() }

mbp.scheduleBuild2(0)
println "job created, webhook registered, indexing scheduled"
GROOVY
ok "job created"

say "Waiting for Jenkins to register the webhook"
HOOK_OK=""
for _ in $(seq 1 30); do
  if gl "$API/projects/$PROJECT_ENC/hooks" \
     | python3 -c 'import sys,json;sys.exit(0 if any("/gitlab-webhook/post" in h["url"] for h in json.load(sys.stdin)) else 1)'; then
    HOOK_OK=1; break
  fi
  sleep 2
done
if [ -n "$HOOK_OK" ]; then
  gl "$API/projects/$PROJECT_ENC/hooks" \
    | python3 -c 'import sys,json;[print("    ok  webhook -> %s  (merge_requests=%s push=%s)" % (h["url"], h["merge_requests_events"], h["push_events"])) for h in json.load(sys.stdin)]'
else
  printf '\n    \033[0;31mFAILED\033[0m  Jenkins did not register a webhook within 60s.\n' >&2
  printf '            Check manageWebHooks in casc/jenkins.yaml, then the Jenkins log:\n' >&2
  printf '            docker logs jenkins 2>&1 | grep -i "web hook"\n\n' >&2
  exit 1
fi

cat <<EOF

  Project  http://${GITLAB_HOST}/${PROJECT_PATH}
  Job      http://${JENKINS_HOST}:${JENKINS_PORT}/job/${JOB_NAME}/

  Now open a merge request and watch the bot see it:
    ./scripts/open-test-mr.sh

EOF
