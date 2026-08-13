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
./scripts/up.sh              # boot GitLab + Jenkins, seed credentials   (~3 min first run)
./scripts/seed-project.sh    # create the console fixture repo and the Jenkins job
./scripts/seed-docs-repo.sh  # create the docs repo DocBot writes to
./scripts/open-test-mr.sh docs
./scripts/docbot-run.sh 1    # <- the merge request number the previous line printed
```

`open-test-mr.sh` opens a real merge request and prints the `verdict.json`
Jenkins produced from it. `docbot-run.sh` then runs the real CLI over the same
merge request and, if the gate says the manual is affected, opens a merge
request on the docs repository linked back to it.

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
| `seed-project.sh` | Create the console fixture project, push it, register the webhook, create the Jenkins job |
| `seed-docs-repo.sh` | Create the docs project, push the fixture manual, protect `main` |
| `open-test-mr.sh [docs\|silent]` | Open a test MR and report what Jenkins decided |
| `docbot-run.sh <iid>` | Run the real CLI over that MR: `gate`, then `propose` |
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

Two fixture repositories, because the design needs two:

| Directory | GitLab project | What it stands in for |
|---|---|---|
| `demo-repo/` | `root/mobivisor-console` | the product repository DocBot watches |
| `docs-repo/` | `root/mobivisor-manual` | the manual repository DocBot writes to |

The separation is the point of foundation doc §7 option B: the bot's write
access reaches a repository that contains no product code, and everything it
does there arrives as a merge request a human has to look at. `main` on the
docs project is protected against direct pushes as well, so the rule does not
depend on DocBot being correct.

### 5.1 Detection — `demo-repo/Jenkinsfile`

The Phase 1 detector. On every merge request it:

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

### 5.2 Delivery — `docbot-run.sh`

The Jenkinsfile stops at a tier-1 verdict. `./scripts/docbot-run.sh <iid>` runs
what the pipeline will actually run, from the laptop:

```
changed files (GitLab API)  ->  docbot gate  ->  docbot propose
```

and, on a positive verdict, opens the docs merge request. Same commands, same
arguments, same artifacts as the eventual Jenkins stage — §8.5 wants the CLI to
run identically in both places, and this is how that stays true rather than
aspirational.

Verified end to end against this stack:

| Run | Result |
|---|---|
| `docbot-run.sh 4` (enrollment change) | tier 2 `mistral-small-latest`, confidence 0.98 → docs MR !1 opened, carrying `doc-impact/pending/mr-4.yaml` |
| second push to the same source MR | record recommitted, MR body rewritten, **still one docs MR** |
| `docbot-run.sh 5` (push transport) | `doc_impact: false` at tier 1 — no model call, no docs MR, nothing written |
| both directions | source MR carries a DocBot comment linking to the docs MR; GitLab cross-references it back |

The middle row is the one worth keeping an eye on. A source merge request is
pushed to repeatedly and the gate re-runs each time; the docs branch is named
after the source MR id so all of them land on one merge request. Nine merge
requests for one change would teach a reviewer to ignore all nine.

`--dry-run` renders the record and the merge-request body to the terminal
without writing anything, which is the fastest way to see what a reviewer would
be shown.

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

- **DocBot does not run inside Jenkins yet.** The controller has no Python and
  no `docbot`, so `docbot-run.sh` drives the pipeline from the laptop instead.
  This is a deliberate ordering, not an oversight: installing the CLI means
  rebuilding the Jenkins image, and that re-resolves every plugin in
  `plugins.txt`, which is unpinned (§7 below). Pin the plugins in the same
  change that adds the CLI, so a broken controller has one suspect rather than
  two.
- **No Docker agent.** Builds run on the Jenkins controller. §8.5 wants the
  DocBot CLI in a pinned image; that is the same change as the point above.
- **No trigger #2.** §8.3's push-to-main drafting run is a stub in the
  `Jenkinsfile`. `docbot propose` runs happily from either trigger, so which
  one it lands on is still an open choice — see `docbot/README.md` §9.
- **Nothing validates the docs merge request.** §6.7 wants a build, a link
  check, a prose lint and a "no edits to `human-only` or `generated` paths"
  gate on it. The first three need the real build script (§12 question #3); the
  fourth needs only the content classes already in the fixture's front matter,
  and is the obvious next thing to write.
- **No commit-status reporting.** `gitlab-plugin` is installed but unwired, so
  the MR page shows no Jenkins status. Detection does not depend on it.
- **No fallback branch indexing.** The multibranch job has no
  `PeriodicFolderTrigger`, so discovery is webhook-only: a dropped delivery
  means the MR is never seen. Acceptable here because `open-test-mr.sh` times
  out visibly; production wants a slow periodic scan behind the webhook.
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

   The JCasC file consequently sets **`manageWebHooks: false`**. It said `true`
   for a while, which was misleading in a way worth avoiding: the config read
   as though Jenkins owned the webhook while the hook that actually existed was
   the one `seed-project.sh` created. The flag governs only hook *creation* on
   the GitLab side — inbound deliveries are served by `GitLabWebHookAction`
   whatever it is set to. Flip it back to `true` if a plugin upgrade fixes the
   credential lookup, and drop the API call from `seed-project.sh` when you do.

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
