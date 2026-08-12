#!/usr/bin/env bash
# Stop the environment but keep all data. Next `up.sh` resumes in seconds.
set -euo pipefail
cd "$(dirname "$0")/.."
docker compose stop
printf '\n  Stopped. Data preserved — ./scripts/up.sh resumes.\n  To free the ~8 GB of volumes as well, run ./scripts/nuke.sh\n\n'
