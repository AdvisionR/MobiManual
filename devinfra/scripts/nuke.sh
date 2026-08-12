#!/usr/bin/env bash
# Complete removal of everything this stack created.
#
# Scope is guaranteed by COMPOSE_PROJECT_NAME: compose only ever touches
# containers, volumes, networks and images it labelled as belonging to this
# project, so this cannot reach any other container you run on this machine.
set -euo pipefail
cd "$(dirname "$0")/.."

# shellcheck disable=SC1091
set -a; source .env; set +a

cat <<EOF

  This removes, for compose project "${COMPOSE_PROJECT_NAME}" only:
    - containers   gitlab, jenkins
    - volumes      gitlab-config, gitlab-logs, gitlab-data, jenkins-home  (~8 GB)
    - network      mobimanual-docbot
    - image        mobimanual/jenkins:local  (locally built)
    - file         .runtime/gitlab.env

  It does NOT touch OrbStack, other containers, or the base images
  (gitlab/gitlab-ce, jenkins/jenkins) — those are removed separately below.

EOF
read -r -p "  Proceed? [y/N] " reply
[[ "$reply" =~ ^[Yy]$ ]] || { echo "  Aborted."; exit 0; }

docker compose down --volumes --rmi local --remove-orphans
rm -f .runtime/gitlab.env
rmdir .runtime 2>/dev/null || true

echo
echo "  Removed. Verifying nothing is left behind:"
leftover_c=$(docker ps -a  --filter "label=com.docker.compose.project=${COMPOSE_PROJECT_NAME}" -q | wc -l | tr -d ' ')
leftover_v=$(docker volume ls --filter "label=com.docker.compose.project=${COMPOSE_PROJECT_NAME}" -q | wc -l | tr -d ' ')
leftover_n=$(docker network ls --filter "label=com.docker.compose.project=${COMPOSE_PROJECT_NAME}" -q | wc -l | tr -d ' ')
printf '    containers left: %s\n    volumes left:    %s\n    networks left:   %s\n' \
  "$leftover_c" "$leftover_v" "$leftover_n"

cat <<'EOF'

  Optional further cleanup:

    # reclaim the ~4 GB of base images
    docker rmi gitlab/gitlab-ce:19.2.2-ce.0 jenkins/jenkins:lts-jdk21

    # delete this directory
    rm -rf "$(pwd)"

    # remove the container runtime itself, if you want nothing left at all
    #   OrbStack menubar -> Settings -> uninstall,  or:
    rm -rf ~/.orbstack ~/.docker && rm -rf /Applications/OrbStack.app

EOF
