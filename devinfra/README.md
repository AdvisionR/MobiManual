# DocBot prototype infrastructure — local GitLab + Jenkins

A disposable stand-in for the real MobiVisor CI environment, for building and
testing the DocBot merge-request detector before it touches anything real.

Everything lives in this one directory and in Docker volumes. Nothing is
installed on macOS — no Java, no Ruby, no `brew services`, no `/etc/hosts`
edits, no `sudo`. Removal is one command.

---

## 1. Prerequisites

**OrbStack**, already installed here. It is the container runtime; the stack
uses one OrbStack-specific feature, explained in §4.

    open -a OrbStack

Nothing else. `up.sh` starts OrbStack itself if it is not running.

---

## 2. Quick start

```bash
./scripts/up.sh             # boot GitLab + Jenkins, seed credentials   (~3 min first run)
./scripts/seed-project.sh   # create the fixture repo and the Jenkins job
./scripts/open-test-mr.sh docs
```

The last command opens a real merge request and prints the `verdict.json`
Jenkins produced from it.

| | URL | Login |
|---|---|---|
| GitLab | http://gitlab.orb.local | `root` / `MobiManualDev!2026` |
| Jenkins | http://jenkins.orb.local:8080 | `admin` / `MobiManualDev!2026` |

Credentials are in [.env](.env). They are local-only throwaways.

---

## 3. What the scripts do

| Script | Purpose |
|---|---|
| `up.sh` | Start OrbStack, boot GitLab, wait for real readiness, seed it, build and boot Jenkins |
| `seed-gitlab.sh` | Set root password, allow local-network webhooks, mint a Jenkins API token |
| `seed-project.sh` | Create the fixture project, push it, register the webhook, create the Jenkins job |
| `open-test-mr.sh [docs\|silent]` | Open a test MR and report what Jenkins decided |
| `status.sh` | Containers, memory, disk, and four-way reachability check |
| `down.sh` | Stop everything, keep data |
| `nuke.sh` | Remove everything this stack created |
| `jenkins-groovy.sh` | Run a Groovy script against the Jenkins script console |

---

## 4. Why `*.orb.local` and not `localhost`

This is the design decision that makes the rest simple, so it is worth
understanding before changing anything.

Three parties need to agree on what to call each service:

- your **browser**, on macOS
- **Jenkins**, cloning and calling the GitLab API from inside a container
- **GitLab**, POSTing webhooks to Jenkins from inside a different container

`localhost` cannot satisfy all three: inside the Jenkins container, `localhost`
is Jenkins. The usual workarounds are `/etc/hosts` entries (needs `sudo`,
leaves residue) or `host.docker.internal` (does not work from the browser).

OrbStack publishes `<container-name>.orb.local` and resolves it **both** from
macOS and from inside other containers. One name is correct everywhere, so:

- no ports are published — nothing is claimed on the macOS side, and this stack
  cannot collide with the `req-eng-*` containers already on this machine
- no `/etc/hosts` edits, no `sudo`
- GitLab's `external_url` is the same URL the browser uses, so the clone URLs
  and MR links it generates are correct for everyone

This is also load-bearing for a reason that is not obvious: the GitLab Branch
Source plugin **rejects** a Jenkins URL starting with `http://localhost` when
registering webhooks (`IllegalStateException: Jenkins URL cannot start with
http://localhost`). A localhost-based setup fails at exactly the step this
prototype exists to exercise.

**Trade-off:** this ties the stack to OrbStack. On plain Docker Desktop you
would add `/etc/hosts` entries and publish ports instead.

---

## 5. The prototype

`demo-repo/Jenkinsfile` is the Phase 1 detector. On every merge request it:

1. confirms it is an MR (`when { changeRequest() }`) and prints the context
   variables the gate needs — `CHANGE_ID`, `CHANGE_TITLE`, `CHANGE_AUTHOR`,
   `CHANGE_BRANCH`, `CHANGE_TARGET`, `CHANGE_URL`
2. pulls the changed-file list from the **GitLab API**
3. applies the tier-1 path filter from `demo-repo/docs/doc-map.json`
4. writes and archives `verdict.json`

Verified working end to end. Two scenarios:

```bash
./scripts/open-test-mr.sh docs     # -> "doc_impact": true,  area enrollment-ios
./scripts/open-test-mr.sh silent   # -> "doc_impact": false, area push-transport
```

The `silent` case matters as much as the other one. Per foundation doc §14.3,
the gate's job is mostly to say nothing, so "correctly stays quiet" is a result
worth testing rather than an absence of one.

### Two deviations from the foundation doc, on purpose

**Changed files come from the API, not `git merge-base`.** §8.4 gives a
`merge-base` snippet and warns that multibranch checks out a *merge commit* over
a shallow clone. That warning is correct — the build log confirms Jenkins
checks out `cd0e0f3...` merged with `main`, not the branch head. Rather than
tune clone depth, the prototype asks GitLab which files changed. That is
authoritative and needs no checkout behaviour tuning.

**Gate logic is jq, not Groovy.** §8.5 says keep Jenkins thin. The jq filter is
a placeholder standing exactly where `docbot gate` will be dropped in; the doc
map is JSON only because jq reads it. Keep the YAML shape from §6.5 when you
port this to the real CLI.

---

## 6. What is deliberately not set up

- **No Docker agent.** Builds run on the Jenkins controller. §8.5 wants the
  DocBot CLI in a pinned image; that starts mattering when there is a CLI.
- **No trigger #2.** §8.3's push-to-main drafting run is a stub in the
  `Jenkinsfile`.
- **No HTTPS.** Plain HTTP throughout.
- **The forge is assumed to be GitLab.** This is open question #1 in §12. If it
  turns out to be Bitbucket or GitHub Enterprise, this stack's GitLab half is
  wrong, but the Jenkins half and the whole `docbot` CLI shape carry over.

---

## 7. Gotchas found while building this

Recorded because each one cost time and none is discoverable from an error
message alone.

1. **GitLab's bundled healthcheck lies.** `/opt/gitlab/bin/gitlab-healthcheck`
   exits 0 while nginx is still down, so `depends_on: service_healthy` releases
   Jenkins minutes early. The compose file probes `/-/readiness?all=1` instead.
   Also, `/-/health` is not a GitLab endpoint — use `/-/readiness` internally
   and `/users/sign_in` from outside.

2. **`gitlab-rails runner -` needs `docker exec -i`.** Without `-i` the runner
   gets an empty script and exits 0, producing silent no-ops.

3. **GitLab blocks webhooks to private-network addresses by default.** Jenkins
   is on an RFC1918 address, so every delivery is dropped with the hook looking
   correctly configured. `seed-gitlab.sh` sets
   `allow_local_requests_from_web_hooks_and_services`. This is a database
   setting, not an omnibus one.

4. **JCasC symbol names are not guessable.** `loggedInAuthorizationStrategy`
   does not exist — it is `loggedInUsersCanDoAnything`. The credential symbol is
   `gitlabPersonalAccessToken` (lowercase L) while the server block is
   `gitLabServers` (capital L). A wrong symbol crash-loops Jenkins at boot.
   To get ground truth, configure the object via the script console, then:

   ```bash
   ./scripts/jenkins-groovy.sh some-config.groovy
   curl -u admin:PW -b cookies -H "$CRUMB" -X POST \
     http://jenkins.orb.local:8080/configuration-as-code/export
   ```

   (`export` is POST-only; GET returns "Method Not Allowed".)

5. **The Branch Source plugin cannot register its own webhook here.** With
   `manageWebHooks: true` and a valid `credentialsId`, registration aborts:
   `WARNING: No Item credentials added, cannot create web hook`.
   `GitLabSCMSource.credentials()` returns null even though
   `CredentialsProvider.lookupCredentials(PersonalAccessToken, ...)` finds the
   credential in the same context. `seed-project.sh` therefore registers the
   hook via the GitLab API against `/gitlab-webhook/post` — the same endpoint
   the plugin would have used, so runtime behaviour is identical.

---

## 8. Resource use

Measured with both services idle after a full MR build:

| | Memory | Disk |
|---|---|---|
| GitLab | ~3.5 GB | ~500 MB volumes |
| Jenkins | ~750 MB | ~330 MB volume |
| Images | | ~4 GB |

GitLab is tuned down in `docker-compose.yml` (2 Puma workers, reduced Sidekiq
concurrency, Prometheus/KAS/registry off). Stock settings assume a dedicated
8 GB host and will not leave room for Jenkins.

The OrbStack VM is capped at 8 GB, comfortable for both on a 16 GB machine.
Raise it in OrbStack → Settings if you add services.

Both images are **native arm64** — no Rosetta emulation. GitLab boots in about
90 seconds on this M5, not the several minutes an x86 image would take.

---

## 9. Uninstall

Stop for the day, keep everything:

```bash
./scripts/down.sh
```

Remove everything this stack created:

```bash
./scripts/nuke.sh
```

It prompts, then removes the two containers, all four volumes, the network, and
the locally built Jenkins image, and prints a count of anything left over.

**Scope is enforced by Docker labels, not by matching names.** Every resource
carries `com.docker.compose.project=mobimanual`, and `docker compose down` only
touches its own project. Verified on this machine: the `req-eng-*` and
`req2code-tracer` containers and their networks are untouched.

To go all the way back to nothing:

```bash
./scripts/nuke.sh
docker rmi gitlab/gitlab-ce:19.2.2-ce.0 jenkins/jenkins:lts-jdk21   # ~4 GB
rm -rf "$(pwd)"                                                      # this directory
```

And if you want the runtime gone too — note this removes **all** your
containers, including the `req-eng-*` ones:

```
OrbStack → Settings → Uninstall
```

There is nothing else. No launch agents, no `/usr/local` files, no PATH
entries, no `/etc/hosts` lines.
