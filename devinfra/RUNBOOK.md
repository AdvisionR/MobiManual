# Runbook — reproduce and inspect

How to make this template do the thing it exists to do, and how to look at
every stage of it afterwards. Companion to [README.md](README.md), which
explains *why* the pieces are shaped the way they are.

The claim being tested, in one sentence: **opening a merge request in GitLab
runs `docbot` inside Jenkins, with that merge request's context in its
environment.**

---

## 1. Reproduce

### 1.1 From nothing

```bash
cd devinfra
./scripts/up.sh              # OrbStack, GitLab, seed, Jenkins       (~5-10 min cold)
./scripts/seed-project.sh    # GitLab project + Jenkins job + webhook (~1 min)
./scripts/open-test-mr.sh    # push a branch, open an MR, wait, print (~1 min)
```

Every script is idempotent. Re-running `seed-project.sh` deletes and recreates
both the project and the job, which is the fastest way back to a known state.

What each step must print before the next one is worth running:

| Step | The line that means it worked |
|---|---|
| `up.sh` | `ok  Jenkins up at http://jenkins.orb.local:8080` |
| `seed-project.sh` | `ok  webhook -> http://jenkins.orb.local:8080/gitlab-webhook/post  (merge_requests=True push=True)` |
| `open-test-mr.sh` | a `detection.json` body with your MR's title and `src/console.ts` |

The expected end state:

```json
{
  "merge_request": {
    "id": "1",
    "title": "A change the bot should notice (165102)",
    "author": "root",
    "branch": "feature/change-165102",
    "target": "main",
    "url": "http://gitlab.orb.local/root/mobivisor-console/-/merge_requests/1"
  },
  "changed_files": ["src/console.ts"]
}
```

### 1.2 After editing the bot

`docbot` is baked into the Jenkins image, so it needs a rebuild — but nothing
else does:

```bash
docker compose up -d --build jenkins    # ~15 s when only the stub changed
./scripts/open-test-mr.sh               # a second MR; the first one stays open
```

Each `open-test-mr.sh` opens a new merge request, so MR numbers climb. Nothing
cleans them up; `seed-project.sh` wipes the lot by recreating the project.

### 1.3 After editing the Jenkinsfile

The Jenkinsfile lives in the *fixture repo*, so Jenkins only sees it once it is
pushed to GitLab:

```bash
./scripts/seed-project.sh    # re-pushes demo-repo/, recreates the job
./scripts/open-test-mr.sh
```

Editing `demo-repo/Jenkinsfile` and running only `open-test-mr.sh` tests the
*previously pushed* version. This is the easiest way to fool yourself here.

### 1.4 Resetting Jenkins alone

The image is meant to carry the whole controller configuration, so throwing
away Jenkins' state should cost nothing but a re-seed. GitLab is untouched:

```bash
docker compose rm -sfv jenkins
docker volume rm mobimanual_jenkins-home
docker compose up -d jenkins        # back in ~20 s, JCasC reapplied
./scripts/seed-project.sh           # the job is state, so it comes back here
```

If that sequence ever needs a manual step in the Jenkins UI, something has
drifted out of `casc/jenkins.yaml` and into the volume.

---

## 2. Inspect

### 2.1 Did Jenkins see the merge request?

```bash
JK='admin:MobiManualDev!2026'
BASE=http://jenkins.orb.local:8080

# every branch and MR the job has discovered
curl -s -u "$JK" "$BASE/job/docbot/api/json?tree=jobs%5Bname,color%5D" | python3 -m json.tool
```

A discovered merge request appears as a job named `MR-<iid>`:

```json
{"jobs": [{"name": "main", "color": "blue"},
          {"name": "MR-1", "color": "blue"}]}
```

(abridged — each entry also carries a `_class`.)

`blue` is a passing build. No `MR-*` entry at all means detection failed —
go to §3.

### 2.2 What did the bot see?

The artifact:

```bash
curl -s -u "$JK" "$BASE/job/docbot/job/MR-1/1/artifact/detection.json" | python3 -m json.tool
```

The console, which is where the stub's banner and the changed-file list are:

```bash
curl -s -u "$JK" "$BASE/job/docbot/job/MR-1/1/consoleText" | sed -n '/+ docbot/,$p'
```

```
+ docbot

  ┌─ merge request detected ────────────────────────────────
  │  !1  A change the bot should notice (165102)
  │  root: feature/change-165102 -> main
  │  http://gitlab.orb.local/root/mobivisor-console/-/merge_requests/1
  └─────────────────────────────────────────────────────────

  changed files:
    src/console.ts
```

`mr.json` is archived next to it — the raw GitLab API response, if you want to
see every field the bot could have used.

### 2.3 Did it correctly do nothing on a plain branch?

Half the behaviour is the half that stays quiet. The `main` job builds on every
push and must skip the stage. The assertion is the artifact list, not the log:

```bash
curl -s -u "$JK" "$BASE/job/docbot/job/main/lastBuild/api/json?tree=result,artifacts%5BfileName%5D"
```

```json
{"artifacts": [], "result": "SUCCESS"}
```

(abridged — the response also carries a `_class`.)

Green **and** empty is the whole claim, because the two halves cover each other.
`archiveArtifacts` sits inside the guarded stage with no `allowEmptyArchive`, so
a stage that ran on a branch build would reach it with nothing to archive —
`docbot` exits early without writing `detection.json` when `CHANGE_ID` is unset —
and fail the build. `SUCCESS` with an empty list is therefore only reachable by
skipping the stage. If `docbot` executes here, the `when { changeRequest() }`
guard is broken and this build is red.

The matching log line, to see it rather than infer it:

```bash
curl -s -u "$JK" "$BASE/job/docbot/job/main/lastBuild/consoleText" \
  | grep -F 'Stage "DocBot" skipped due to when conditional'
```

Match the full string. `grep -E 'Skipping|skipped'` also catches `First time
build. Skipping changelog.`, which the git plugin prints on every first build —
MR builds included — so that pattern reports success whether or not the guard
works. Use `lastBuild` rather than a pinned `/1` for the reason in §1.3: after a
re-seed, build 1 is a different build than the one you think you are reading.

### 2.4 Run the bot by hand, without Jenkins

The fastest loop while writing a real bot. The container already has the token
in its environment as `GITLAB_PAT`, so nothing needs to be passed in:

```bash
docker exec \
  -e CHANGE_ID=1 \
  -e CHANGE_TITLE="hand-run" \
  -e CHANGE_AUTHOR=root \
  -e CHANGE_BRANCH=feature/x \
  -e CHANGE_TARGET=main \
  -e CHANGE_URL=http://gitlab.orb.local/root/mobivisor-console/-/merge_requests/1 \
  -e GITLAB_URL=http://gitlab.orb.local \
  -e GITLAB_PROJECT=root/mobivisor-console \
  jenkins sh -c 'cd /tmp && GITLAB_TOKEN=$GITLAB_PAT docbot'
```

Same banner, same `detection.json`, no build, no webhook, no waiting. And the
no-context path:

```bash
docker exec jenkins sh -c 'cd /tmp && docbot'
# docbot: not a merge request — nothing to do
```

### 2.5 The GitLab side

```bash
set -a; source .runtime/gitlab.env; set +a     # GITLAB_PAT
API=http://gitlab.orb.local/api/v4/projects/root%2Fmobivisor-console
glget() { curl -s -H "PRIVATE-TOKEN: $GITLAB_PAT" "$@"; }   # `gl` is a common alias

glget "$API/hooks" | python3 -m json.tool           # the webhook Jenkins registered
glget "$API/merge_requests?state=opened" | python3 -c \
  'import sys,json;[print("!%(iid)s %(title)s"%m) for m in json.load(sys.stdin)]'
```

Webhook deliveries — the single most useful page when detection is silent —
are in the UI, and also over the API:

```bash
HOOK=$(glget "$API/hooks" | python3 -c 'import sys,json;print(json.load(sys.stdin)[0]["id"])')
glget "$API/hooks/$HOOK/events" | python3 -c \
  'import sys,json;[print(e["created_at"], e["trigger"], "->", e["response_status"]) for e in json.load(sys.stdin)]'
```

```
2026-08-18T14:51:03.971Z merge_request_hooks -> 200
2026-08-18T14:51:03.445Z push_hooks -> 200
```

Two deliveries per `open-test-mr.sh` run — the branch push and the merge
request — both answered `200` by Jenkins. Anything other than `200`, or no rows
at all, and the problem is on this side of the wire.


    http://gitlab.orb.local/root/mobivisor-console/-/hooks

The commit status Jenkins posts back (`jenkinsci/mr-merge`) — this is what
turns the MR page green, and the Branch Source plugin does it unprompted:

```bash
SHA=$(glget "$API/merge_requests/1" | python3 -c 'import sys,json;print(json.load(sys.stdin)["sha"])')
glget "$API/repository/commits/$SHA/statuses" | python3 -c \
  'import sys,json;[print(s["name"], s["status"], s["target_url"]) for s in json.load(sys.stdin)]'
```

### 2.6 The stack itself

```bash
./scripts/status.sh                      # containers, memory, disk, 4-way reachability
docker logs jenkins 2>&1 | grep -iE 'casc|severe|exception'   # silence is correct
docker exec jenkins ls -l /usr/local/bin/docbot                # the bot that is installed
```

`status.sh`'s reachability block is the one to read first when anything is
strange: it checks host→GitLab, host→Jenkins, Jenkins→GitLab **and**
GitLab→Jenkins, and the last one is the direction webhooks travel.

---

## 3. When it does not work

| Symptom | First thing to check |
|---|---|
| `seed-project.sh` fails at "Waiting for Jenkins to register the webhook" | `manageWebHooks: true` in `casc/jenkins.yaml`, then `docker logs jenkins 2>&1 \| grep -i "web hook"`. See README §7.5 — registration also needs the `afterSave()` call the script makes. |
| MR opens, but no `MR-<iid>` job appears | Webhook deliveries (§2.5). A delivery with status 0 or a connection error means GitLab cannot reach Jenkins — usually `allow_local_requests_from_web_hooks_and_services`, re-applied by `./scripts/seed-gitlab.sh` (README §7.3). |
| `MR-<iid>` job exists but the build fails in `docbot` | `consoleText` (§2.2). A 401 from curl means the `gitlab-http` credential is stale — re-run `./scripts/seed-gitlab.sh`, then `docker compose up -d --force-recreate jenkins` so JCasC picks up the new token. |
| Jenkins restarts in a loop | JCasC rejected the config: `docker logs jenkins 2>&1 \| head -50`. A wrong symbol name is the usual cause (README §7.4). |
| Everything is slow / GitLab returns 502 | GitLab is still booting. `docker inspect --format '{{.State.Health.Status}}' gitlab` must say `healthy`. |
| The build runs the old Jenkinsfile | It was never pushed — see §1.3. |

---

## 4. Teardown

```bash
./scripts/down.sh    # stop, keep all data; up.sh resumes in seconds
./scripts/nuke.sh    # remove containers, volumes, network, built image (prompts)
```

Both are scoped by the `com.docker.compose.project=mobimanual` label, so
neither touches anything else running on the machine.

---

## 5. Last verified

2026-08-18, on this machine, in this order:

1. `docker compose build jenkins` — plugin set resolves to 66 plugins from the
   4 named in `plugins.txt`
2. `docker compose rm -sfv jenkins` + `docker volume rm mobimanual_jenkins-home`
   + `docker compose up -d jenkins` — fresh controller up in ~20 s, JCasC applied
   with no errors in the log
3. `./scripts/seed-project.sh` — project, job and webhook created; webhook
   verified present with `merge_requests=True`
4. `./scripts/open-test-mr.sh` — MR !1 detected, build succeeded,
   `detection.json` listed `src/console.ts`
5. `main` branch build — `Stage "DocBot" skipped due to when conditional`,
   `Finished: SUCCESS`
6. hand-run of `docbot` inside the container, with and without `CHANGE_ID` —
   both paths as documented in §2.4

Not exercised in that pass: a cold `up.sh` from no GitLab volumes, because it
would have destroyed the running instance. The GitLab half of the stack has
been up since before these changes.
