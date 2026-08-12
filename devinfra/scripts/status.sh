#!/usr/bin/env bash
# What is running, what it costs, and whether the two halves can see each other.
set -euo pipefail
cd "$(dirname "$0")/.."

# shellcheck disable=SC1091
set -a; source .env; set +a

printf '\n\033[1mContainers\033[0m\n'
docker compose ps --format 'table {{.Service}}\t{{.Status}}' 2>/dev/null || echo "  (stack is down)"

printf '\n\033[1mResource use\033[0m\n'
docker stats --no-stream --format 'table {{.Name}}\t{{.MemUsage}}\t{{.CPUPerc}}' gitlab jenkins 2>/dev/null \
  || echo "  (nothing running)"

printf '\n\033[1mDisk (volumes)\033[0m\n'
docker system df -v 2>/dev/null | awk '/VOLUME NAME/{f=1} f && /mobimanual/ {printf "  %-34s %s\n", $1, $3}'

printf '\n\033[1mReachability\033[0m\n'
chk() { # label url
  code=$(curl -s -o /dev/null -w '%{http_code}' --max-time 5 "$2" 2>/dev/null || echo 000)
  [ "$code" != "000" ] && printf '  \033[0;32mok\033[0m   %-28s %s (HTTP %s)\n' "$1" "$2" "$code" \
                       || printf '  \033[0;31mFAIL\033[0m %-28s %s\n' "$1" "$2"
}
chk "host -> GitLab"  "http://${GITLAB_HOST}/users/sign_in"
chk "host -> Jenkins" "http://${JENKINS_HOST}:${JENKINS_PORT}/login"

if docker ps --format '{{.Names}}' | grep -q '^jenkins$'; then
  if docker exec jenkins curl -sf -o /dev/null --max-time 5 "http://${GITLAB_HOST}/users/sign_in"; then
    printf '  \033[0;32mok\033[0m   %-28s %s\n' "Jenkins -> GitLab" "http://${GITLAB_HOST}"
  else
    printf '  \033[0;31mFAIL\033[0m %-28s %s\n' "Jenkins -> GitLab" "http://${GITLAB_HOST}"
  fi
fi
if docker ps --format '{{.Names}}' | grep -q '^gitlab$'; then
  if docker exec gitlab curl -sf -o /dev/null --max-time 5 "http://${JENKINS_HOST}:${JENKINS_PORT}/login"; then
    printf '  \033[0;32mok\033[0m   %-28s %s\n' "GitLab -> Jenkins" "http://${JENKINS_HOST}:${JENKINS_PORT}"
  else
    printf '  \033[0;31mFAIL\033[0m %-28s %s\n' "GitLab -> Jenkins" "http://${JENKINS_HOST}:${JENKINS_PORT}"
  fi
fi
printf '\n'
