#!/usr/bin/env bash
# Apply the GitLab-side configuration the Jenkins integration depends on.
# Idempotent: re-running rotates the token and re-asserts the settings.
set -euo pipefail
cd "$(dirname "$0")/.."

# shellcheck disable=SC1091
set -a; source .env; set +a

ok() { printf '    \033[0;32mok\033[0m  %s\n' "$*"; }

# `gitlab-rails runner` is the supported way to drive an omnibus instance
# non-interactively. Everything below is plain ActiveRecord against GitLab's
# own models, so it survives version bumps better than screen-scraping the UI.
# -i is required: `gitlab-rails runner -` reads the script from stdin, and
# without it docker exec attaches no stdin and the runner silently gets nothing.
TOKEN=$(docker exec -i \
  -e SEED_ROOT_PW="${GITLAB_ROOT_PASSWORD}" \
  gitlab gitlab-rails runner - <<'RUBY' 2>/dev/null | sed -n 's/^SEEDED_TOKEN=//p' | tail -1
  # --- 1. Deterministic root password -------------------------------------
  # GITLAB_ROOT_PASSWORD only applies on very first boot; re-asserting it here
  # keeps the documented credentials true even after a partial re-seed.
  root = User.find_by_username('root')
  root.password = root.password_confirmation = ENV['SEED_ROOT_PW']
  root.password_automatically_set = false
  root.skip_reconfirmation!
  root.save!

  # --- 2. Allow webhooks to reach the local network -----------------------
  # Jenkins lives on an RFC1918 address. Without this, GitLab accepts the
  # webhook config and then silently drops every delivery.
  s = ApplicationSetting.current_without_cache || ApplicationSetting.create_from_defaults
  s.allow_local_requests_from_web_hooks_and_services = true

  # --- 3. No Auto DevOps --------------------------------------------------
  # Jenkins is the executor, and this instance deliberately has no runner.
  # With Auto DevOps on, every push to a project without a .gitlab-ci.yml
  # starts a generated build/test/scan pipeline that waits for a runner
  # forever and shows "stuck" on every commit and merge request. Instance-wide
  # rather than per project, so projects created later are covered too.
  s.auto_devops_enabled = false
  s.save!

  # --- 4. A personal access token for Jenkins -----------------------------
  # Read the generated value back rather than forcing one: GitLab validates
  # token format, and the generated token is guaranteed to satisfy it.
  root.personal_access_tokens.where(name: 'jenkins-docbot').find_each(&:revoke!)
  t = root.personal_access_tokens.create!(
    name:       'jenkins-docbot',
    scopes:     [:api, :read_repository, :write_repository],
    expires_at: 300.days.from_now
  )
  # Prefixed so the value survives any warning noise the runner prints.
  puts "SEEDED_TOKEN=#{t.token}"
RUBY
)

if [ -z "${TOKEN}" ] || [ "${TOKEN:0:6}" != "glpat-" ]; then
  echo "    !! failed to mint a GitLab token (got: '${TOKEN:0:20}')" >&2
  echo "    !! retry with: docker compose logs --tail 40 gitlab" >&2
  exit 1
fi

mkdir -p .runtime
printf 'GITLAB_PAT=%s\n' "$TOKEN" > .runtime/gitlab.env
chmod 600 .runtime/gitlab.env

ok "root password asserted"
ok "local-network webhooks allowed"
ok "Auto DevOps disabled"
ok "token minted -> .runtime/gitlab.env"

# Prove the token actually works before Jenkins depends on it.
if curl -sf -H "PRIVATE-TOKEN: ${TOKEN}" "http://${GITLAB_HOST}/api/v4/user" >/dev/null; then
  ok "token verified against GitLab API"
else
  echo "    !! token did not authenticate against the API" >&2
  exit 1
fi
