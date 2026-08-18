#!/usr/bin/env bash
# Bring up the whole prototype environment, in dependency order.
# Safe to re-run: every step is idempotent.
set -euo pipefail
cd "$(dirname "$0")/.."

# shellcheck disable=SC1091
set -a; source .env; set +a

say()  { printf '\n\033[1;36m==>\033[0m %s\n' "$*"; }
ok()   { printf '    \033[0;32mok\033[0m  %s\n' "$*"; }
warn() { printf '    \033[0;33m!!\033[0m  %s\n' "$*"; }

# compose parses env_file for every service on every invocation, so this must
# exist before the first `docker compose` call, even when only starting GitLab.
mkdir -p .runtime
[ -f .runtime/gitlab.env ] || echo "GITLAB_PAT=placeholder" > .runtime/gitlab.env

if ! docker info >/dev/null 2>&1; then
  say "Starting OrbStack"
  open -a OrbStack
  for _ in $(seq 1 60); do docker info >/dev/null 2>&1 && break; sleep 1; done
  docker info >/dev/null 2>&1 || { echo "OrbStack did not start"; exit 1; }
fi
ok "container runtime up"

say "Starting GitLab (first boot takes 4-8 minutes; it is compiling its own config)"
docker compose up -d gitlab

printf '    waiting for GitLab health'
deadline=$((SECONDS + 900))
while true; do
  status=$(docker inspect --format '{{.State.Health.Status}}' gitlab 2>/dev/null || echo missing)
  [ "$status" = "healthy" ] && break
  if [ "$SECONDS" -gt "$deadline" ]; then
    printf '\n'; warn "GitLab not healthy after 15 min (status: $status)"
    warn "inspect with: docker compose logs --tail 80 gitlab"
    exit 1
  fi
  printf '.'; sleep 10
done
printf '\n'; ok "GitLab healthy at http://${GITLAB_HOST}"

say "Seeding GitLab (root password, webhook policy, Jenkins access token)"
./scripts/seed-gitlab.sh

say "Building and starting Jenkins"
docker compose up -d --build jenkins

printf '    waiting for Jenkins'
deadline=$((SECONDS + 300))
until curl -sf -o /dev/null "http://${JENKINS_HOST}:${JENKINS_PORT}/login"; do
  if [ "$SECONDS" -gt "$deadline" ]; then
    printf '\n'; warn "Jenkins did not come up"
    warn "inspect with: docker compose logs --tail 80 jenkins"
    exit 1
  fi
  printf '.'; sleep 3
done
printf '\n'; ok "Jenkins up at http://${JENKINS_HOST}:${JENKINS_PORT}"

cat <<EOF

  GitLab    http://${GITLAB_HOST}          root / ${GITLAB_ROOT_PASSWORD}
  Jenkins   http://${JENKINS_HOST}:${JENKINS_PORT}     ${JENKINS_ADMIN_ID} / ${JENKINS_ADMIN_PASSWORD}

  Next:  ./scripts/seed-project.sh   # create the GitLab project and the Jenkins job
  Stop:  ./scripts/down.sh           # keeps all data
  Wipe:  ./scripts/nuke.sh           # removes everything this stack created

EOF
