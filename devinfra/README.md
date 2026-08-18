# DocBot template — GitLab + Jenkins merge-request detection

A local GitLab and a local Jenkins, wired together so that **opening a merge
request runs your bot**, with the merge request's context already in its hands.

There is no bot here. `jenkins/docbot` is a stub that reports what it was given
and exits; replacing it is the entire job. Everything else in this directory
exists to get it called at the right moment.

```
  git push  ->  merge request  ->  GitLab webhook  ->  Jenkins discovers MR-<iid>
                                                            |
                                       when { changeRequest() } in the Jenkinsfile
                                                            |
                                                          docbot
                                                (CHANGE_ID, CHANGE_TITLE, ...)
```

Nothing is installed on macOS — no Java, no Ruby, no `brew services`, no
`/etc/hosts` edits, no `sudo`. Everything lives in this directory and in Docker
volumes, and removal is one command.

---

## 1. Prerequisites

**OrbStack.** It is the container runtime, and the stack uses one
OrbStack-specific feature (§6). `up.sh` starts it if it is not running.

---

## 2. Quick start

```bash
./scripts/up.sh              # boot GitLab + Jenkins, seed credentials  (~5 min first run)
./scripts/seed-project.sh    # create the GitLab project and the Jenkins job
./scripts/open-test-mr.sh    # open a merge request, watch the bot see it
```

The last line prints the `detection.json` the bot produced, which looks like:

```json
{
  "merge_request": {
    "id": "1",
    "title": "A change the bot should notice (143022)",
    "author": "root",
    "branch": "feature/change-143022",
    "target": "main",
    "url": "http://gitlab.orb.local/root/mobivisor-console/-/merge_requests/1"
  },
  "changed_files": ["src/console.ts"]
}
```

| | URL | Login |
|---|---|---|
| GitLab | http://gitlab.orb.local | `root` / `MobiManualDev!2026` |
| Jenkins | http://jenkins.orb.local:8080 | `admin` / `MobiManualDev!2026` |

Credentials are in [.env](.env). They are local-only throwaways.

---

## 3. How the detection works

Four moving parts, one per file.

**`jenkins/casc/jenkins.yaml`** registers the GitLab server with the Branch
Source plugin and hands it a token. `manageWebHooks: true` is what makes
Jenkins install the project webhook itself, rather than you clicking it in.

**`scripts/seed-project.sh`** creates a *multibranch* job pointing at the
project, with `OriginMergeRequestDiscoveryTrait`. From then on Jenkins treats
every open merge request as a branch called `MR-<iid>` and builds it.

**`demo-repo/Jenkinsfile`** is 25 lines. `when { changeRequest() }` is true
only for those `MR-*` builds. A push to an ordinary branch still gets built —
the job discovers branches too — but the stage is skipped and the build does
nothing. For a merge request, the plugin has already filled the environment:

| Variable | Example |
|---|---|
| `CHANGE_ID` | `1` — the merge request iid |
| `CHANGE_TITLE` | `A change the bot should notice` |
| `CHANGE_AUTHOR` | `root` |
| `CHANGE_BRANCH` | `feature/change-143022` |
| `CHANGE_TARGET` | `main` |
| `CHANGE_URL` | link back to the merge request |

**`jenkins/docbot`** is then run, in the workspace, with those variables plus a
GitLab token bound from the `gitlab-http` credential. It asks the API which
files the merge request touches, writes `detection.json`, and stops.

### Why the changed files come from the API

A multibranch job checks out the *merge result* over a shallow clone, so
`git diff` and `git merge-base` against the target branch are quietly wrong in
this context. Asking GitLab is authoritative and needs no clone-depth tuning.

---

## 4. Where your bot goes

Edit [jenkins/docbot](jenkins/docbot) — replace the marked block at the bottom,
or the whole file — and rebuild:

```bash
docker compose up -d --build jenkins
```

It is baked into the image at `/usr/local/bin/docbot` rather than living in the
watched repository, because a bot that reviews a repo should not be edited by
the merge requests it reviews. The Jenkinsfile only ever calls `docbot`, so a
real CLI in a pinned image is a drop-in replacement for the stub.

Keep the decisions in there and out of the `Jenkinsfile`: a script can be run
and tested on a laptop, and Groovy inside a pipeline cannot.

---

## 5. Scripts

| Script | Purpose |
|---|---|
| `up.sh` | Start OrbStack, boot GitLab, wait for real readiness, seed it, build and boot Jenkins |
| `seed-gitlab.sh` | Set root password, allow local-network webhooks, mint a Jenkins API token |
| `seed-project.sh` | Create the project, push `demo-repo/`, create the Jenkins job, verify the webhook |
| `open-test-mr.sh` | Open a merge request and print what the bot detected |
| `status.sh` | Containers, memory, disk, and four-way reachability check |
| `down.sh` | Stop everything, keep data |
| `nuke.sh` | Remove everything this stack created |
| `jenkins-groovy.sh` | Run a Groovy script against the Jenkins script console |

---

## 6. Why `*.orb.local` and not `localhost`

Three parties must agree on what to call each service: your **browser** on
macOS, **Jenkins** calling the GitLab API from inside a container, and
**GitLab** POSTing webhooks to Jenkins from a different container. `localhost`
cannot satisfy all three — inside the Jenkins container, `localhost` is
Jenkins.

OrbStack publishes `<container-name>.orb.local` and resolves it both from macOS
and from inside other containers, so one name is correct everywhere: no
published ports, no `/etc/hosts` edits, no `sudo`, and the URLs GitLab
generates are right for everyone.

This is also load-bearing in a way that is not obvious: the GitLab Branch
Source plugin **rejects** a Jenkins URL starting with `http://localhost` when
registering webhooks (`IllegalStateException: Jenkins URL cannot start with
http://localhost`). A localhost-based setup fails at exactly the step this
template exists to demonstrate.

**Trade-off:** this ties the stack to OrbStack. On plain Docker Desktop you
would add `/etc/hosts` entries and publish ports instead.

---

## 7. Things that cost time to discover

Each of these fails silently. None is discoverable from an error message.

1. **GitLab's bundled healthcheck lies.** `/opt/gitlab/bin/gitlab-healthcheck`
   exits 0 while nginx is still down, so `depends_on: service_healthy` releases
   Jenkins minutes early. The compose file probes `/-/readiness?all=1` instead.
   (`/-/health` is not a GitLab endpoint; use `/-/readiness` internally and
   `/users/sign_in` from outside.)

2. **`gitlab-rails runner -` needs `docker exec -i`.** Without `-i` the runner
   reads an empty script and exits 0 — a silent no-op.

3. **GitLab blocks webhooks to private-network addresses by default.** Jenkins
   is on an RFC1918 address, so every delivery is dropped while the hook looks
   correctly configured. `seed-gitlab.sh` sets
   `allow_local_requests_from_web_hooks_and_services`. It is a database
   setting, not an omnibus one.

4. **JCasC symbol names are not guessable.** `loggedInAuthorizationStrategy`
   does not exist — it is `loggedInUsersCanDoAnything`. The credential symbol
   is `gitlabPersonalAccessToken` (lowercase "l") while the server block is
   `gitLabServers` (capital "L"). A wrong symbol crash-loops Jenkins at boot.
   To get ground truth, configure the object via the script console, then:

   ```bash
   ./scripts/jenkins-groovy.sh some-config.groovy
   curl -u admin:PW -b cookies -H "$CRUMB" -X POST \
     http://jenkins.orb.local:8080/configuration-as-code/export
   ```

   (`export` is POST-only; GET returns "Method Not Allowed".)

5. **Webhook registration needs two things, and one is not in the config.**
   `manageWebHooks: true` *plus* an explicit `afterSave()` call.

   `GitLabHookCreator.register()` switches on the source's webhook mode, which
   defaults to `SYSTEM`. That branch opens with
   `if (!server.isManageWebHooks()) return;`, so with the flag false it returns
   before it ever looks at a credential — silently, no log line.

   The second half: registration is triggered by `SCMSource.afterSave()`, and
   `branch-api` only calls that from the UI's form-submit path.
   `WorkflowMultiBranchProject` has no `afterSave()` of its own, so the
   `mbp.save()` in `seed-project.sh` does not reach the sources. A job built
   programmatically must call it — hence `mbp.SCMSources.each { it.afterSave() }`.
   The script then *verifies* the hook exists rather than assuming it: a
   missing hook means merge requests are never detected, and the failure looks
   exactly like Jenkins being slow.

   Do not switch to `webHookMode: ITEM` to work around this. That path calls
   `GitLabSCMSource.credentials()`, which returns null because system-store
   credentials only resolve under `ACL.SYSTEM` while the plugin passes
   `Jenkins.getAuthentication()`.

---

## 8. Deliberately not here

Everything past detection. No build agent — jobs run on the controller — no
HTTPS, and no periodic branch indexing, so discovery is webhook-only: a dropped
delivery means the merge request is never seen. `open-test-mr.sh` times out
visibly when that happens; production wants a slow periodic scan behind the
webhook.

One thing you get for free and may not expect: the Branch Source plugin posts a
commit status back to the merge request by itself (`jenkinsci/mr-merge`), so the
MR page turns green when the bot finishes. Nothing in this repository wires
that up.

---

## 9. Resource use and removal

Measured with both services idle after a build: GitLab ~3.5 GB RSS and ~500 MB
of volumes, Jenkins ~750 MB and ~330 MB, images ~4 GB. GitLab is tuned down in
`docker-compose.yml` (2 Puma workers, reduced Sidekiq concurrency,
Prometheus/KAS/registry off); stock settings assume a dedicated 8 GB host and
leave no room for Jenkins.

```bash
./scripts/down.sh    # stop, keep all data
./scripts/nuke.sh    # remove containers, volumes, network, built image
```

Scope is enforced by the `com.docker.compose.project=mobimanual` label, not by
matching names, so neither touches anything else you run.
