# DocBot template — GitLab + Jenkins merge detection

A local GitLab and a local Jenkins, wired together so that **a merge request
landing on `main` runs your bot**, with that merge request's context already in
its hands.

The bot lives in the fixture, at `demo-repo/tools/docbot/`: a Python CLI that
the Jenkinsfile installs and runs. For every merge it opens a docs merge request
against the same repository, with edits to the manual pages the merge affects,
drafted by a model (Mistral, for the prototype). Everything else in this
directory exists to get it called at the right moment.

```
  merge request merged  ->  GitLab webhook  ->  Jenkins builds main
                                                       |
                                    when { branch 'main' } in the Jenkinsfile
                                                       |
                                          python -m docbot update-manual
                              (git rev-parse HEAD -> which merge request?
                               -> docs merge request from docbot/mr-<iid>)
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
./scripts/open-test-mr.sh --merge            # a real change worth documenting: merge it, watch the bot
./scripts/open-test-mr.sh refactor --merge   # a real change not worth documenting
```

`demo-repo/` is the fixture that gets pushed: a **monorepo**, with the
console under `public/app/` and the user manual under `public/doc/`, so a merge
request can touch either half or both. `open-test-mr.sh` takes one of two kinds
of argument:

- **A scenario**, from [scenarios/](scenarios/README.md): a real change with a
  developer's title and description, and an expected outcome. It tests what the
  model makes of a change. The default, `ios-department`, is worth documenting,
  and `refactor` is not.
- **A kind** (`code`, `docs`, `internal`, `both`, …): a comment appended to one
  part of the monorepo. It tests which paths DocBot ignores and which reach the
  model. [demo-repo/README.md](demo-repo/README.md) lists them.

`./scripts/open-test-mr.sh --help` lists both.

The last lines summarise the `result.json` the build archived:

```
  outcome  opened
  docs MR  !2  http://gitlab.orb.local/root/mobivisor-console/-/merge_requests/2
```

`result.json` itself also names the source merge request, the branch and the
manual diff. The outcome is one of `opened`, `exists` (a rebuild found the docs
merge request it opened before), `skipped` (not a merge, or DocBot's own) and
`error`.

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
project, with `BranchDiscoveryTrait` and `OriginMergeRequestDiscoveryTrait`. So
Jenkins builds `main`, and also builds every open merge request as a branch
called `MR-<iid>`.

**`demo-repo/Jenkinsfile`** guards its one stage on `when { branch 'main' }`.
The `MR-*` builds still run — they just skip the stage and do nothing. The bot
fires **after** a merge request lands, not while it is open.

That is a deliberate move away from the obvious `when { changeRequest() }`. A
documentation bot describes what the product does, and an open merge request may
still be force-pushed, reworked or closed — drafting against one means drafting
against a moving target and discarding the draft each time the branch changes.

It is also the delivery model the foundation doc chose. Model **A**, an advisory
comment on the open merge request, is the `changeRequest()` shape and a good
pilot; model **B**, a bot-authored docs merge request on merge linked back to
the source one, is the destination — and `branch 'main'` is what B needs. The
cost is that the bot can no longer put the documentation *into* the merge
request that changed the code, which is the one thing the monorepo would
otherwise make easy.

**`demo-repo/tools/docbot/`** is then installed into a venv in the workspace
and run with a GitLab token bound from the `docbot-gitlab-token` credential and
the model key from `docbot-llm-key` — and with no merge-request context at all. It works that out for itself.

### Why the merge request is derived, not received

`CHANGE_ID` and friends exist only on `MR-*` builds; a `main` build has none of
them. So docbot starts from the commit in the workspace and asks GitLab what
produced it:

```
GET /projects/:id/repository/commits/:sha/merge_requests
```

then keeps the one that is `merged`, targets `main`, and whose
`merge_commit_sha` or `squash_commit_sha` is that commit. The match is exact
because that endpoint also returns merge requests that merely *contain* the
commit, which is a different question.

Deriving the answer from repository state rather than from the event that
started the build is the property worth having: a forced rebuild, a replay and a
re-index all resolve to the same merge request, and a direct push to `main`
resolves to none — which is a correct answer, not an error.

Two failure modes must not collapse into one, so the HTTP status is inspected
rather than treated as one kind of error:

| Status | Meaning | docbot |
|---|---|---|
| 200 | GitLab knows the commit | resolve the merge request, or find none |
| 404 | GitLab has never seen it — an `MR-*` build checks out a merge *result* built locally and never pushed | exit 0, nothing to do |
| anything else | usually 401 from a stale `docbot-gitlab-token` credential | exit 1, **fail the build** |

A stale credential that resolved to "nothing to do" would look exactly like a
quiet, working bot.

### Why the changed files come from the API

Once docbot has the merge request, `/merge_requests/:iid/diffs` supplies its
per-file diffs, renames included, and `doc-map.json`, `gruntfile.js` and the
manual pages are read with `/repository/files/…/raw?ref=<merge commit>`, so the
draft starts from the manual as it was at the merge.

A local `git diff HEAD^ HEAD` would agree on the `main` build, which is a full
clone of an ordinary branch. It would stop agreeing the moment the stage is
moved or the job gains a clone-depth trait, and it cannot answer the other two
questions docbot has to ask anyway: who opened the merge request, and what
labels does it carry.

### The bot's own merge requests

DocBot's output is a merge request against the repository it watches, so merging
it builds `main`, which runs DocBot. docbot labels every merge request it opens
`docbot-generated`, and cuts the loop by skipping any merge request with that
label. `seed-project.sh` creates the label up front.

The fixture cuts it a second time, in `doc-map.json`, which ignores changes
under `^public/doc/`. That one covers what a label cannot: a human editing the
manual by hand.

---

## 4. Where your bot goes

In the fixture, at [demo-repo/tools/docbot/](demo-repo/tools/docbot/). It is a
Python package that the Jenkinsfile installs into a venv in the workspace, from
a hash-locked `requirements.txt`, and runs as `python -m docbot update-manual`.
Nothing of the bot is baked into the Jenkins image.

It lives in the watched repository because that is how it will reach the real
one: integration means copying the directory and the Jenkinsfile stage.
[docs/docbot-code-location.md](../docs/docbot-code-location.md) weighs this
against a separate image and explains when the bot should move out. To ship a
change into the stack, re-seed with `./scripts/seed-project.sh`.

The decisions are in `src/docbot/drafting/`: which changed files matter, which
pages triage names, and the edits drafting proposes. Keep them in the package
and out of the `Jenkinsfile`: a CLI can be run and
tested on a laptop, and Groovy inside a pipeline cannot. That is not a
stylistic preference — it is what makes this loop possible, with no build, no
webhook and no waiting:

```bash
export DOCBOT_GITLAB_URL=http://gitlab.orb.local DOCBOT_PROJECT=root/mobivisor-console
export DOCBOT_GITLAB_TOKEN=$(sed -n 's/^GITLAB_PAT=//p' .runtime/gitlab.env)
cd demo-repo/tools/docbot
git -C ../../../.runtime/mr-work fetch -q   # the clone open-test-mr.sh made, now with the merge commit
uv run --env-file .env docbot update-manual --sha <a merge commit on main> --repo ../../../.runtime/mr-work --dry-run   # .env holds the model key
uv run pytest
```

Drafting searches the code at the merge commit, so `--repo` names a clone of the
project that has it. `--diff-only` drafts from the diff alone and needs no clone.

The fixture is too small to judge the model, so triage and drafting are also
replayed on real history. Zulip keeps its help centre in its repository, and
`zulip/cases.json` lists commits that changed the product and the help pages together,
and commits that change nothing a user sees. For each one, triage decides whether the
code change has doc impact, and drafting finds and edits pages in the whole help
centre as it was before. The author's own edit is the reference:

```bash
./scripts/fetch-zulip.sh
cd demo-repo/tools/docbot
uv run --env-file .env pytest -m live -s -k zulip   # results in devinfra/.runtime/zulip-results/
```

`--dry-run` prints the manual diff and writes nothing. Without it, the same
command opens the docs merge request exactly as Jenkins would. Against a commit
that is not a merge, it reports `not a merge to main, nothing to do`. Both are
worth seeing.

Jenkins reads the model key from the same `demo-repo/tools/docbot/.env`, which
compose passes to the container when it starts. CasC turns `MISTRAL_API_KEY`
into the `docbot-llm-key` credential. After changing the key, recreate Jenkins
with `docker compose up -d jenkins`. Without the file, the credential is empty
and the DocBot stage fails with a configuration error. Like `GITLAB_PAT`, the
key is then also in the environment of every build on this Jenkins, a shortcut
only acceptable for the local stack.

---

## 5. Scripts

| Script | Purpose |
|---|---|
| `up.sh` | Start OrbStack, boot GitLab, wait for real readiness, seed it, build and boot Jenkins |
| `seed-gitlab.sh` | Set root password, allow local-network webhooks, mint a Jenkins API token |
| `seed-project.sh` | Create the project, push `demo-repo/`, create the Jenkins job, verify the webhook |
| `open-test-mr.sh` | Open a merge request from a scenario (a real change) or a kind (a comment in a chosen part of the monorepo); `--merge` lands it and prints what the bot did |
| `status.sh` | Containers, memory, disk, and four-way reachability check |
| `down.sh` | Stop everything, keep data |
| `nuke.sh` | Remove everything this stack created |
| `jenkins-groovy.sh` | Run a Groovy script against the Jenkins script console |
| `fetch-zulip.sh` | Clone zulip/zulip (bare, `main` only, history since 2026-04-28, about 60 MB) into `.runtime/zulip.git`, or fetch new commits. Triage and drafting are replayed on the commits in `zulip/cases.json`. Needs no stack |

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
MR page turns green on its own. Nothing in this repository wires that up — and
note it says nothing about the bot, which does not run on that build. It is the
`MR-*` build going green with the DocBot stage skipped.

**One build can cover several merges.** Jenkins coalesces queued builds for a
branch. Merge two merge requests in quick succession and `main` may build once,
with HEAD at the second merge commit; the first is then never any build's HEAD,
and docbot never sees it. There is no error and no artifact — nothing that reads
as a failure. For a bot that only reports, that is a missing line in a log; for
one that writes documentation, a docs update dropped in silence.

The fix is not a cleverer diff. Walking `GIT_PREVIOUS_SUCCESSFUL_COMMIT..HEAD`
would close it cheaply and cost exactly the property §3 is built on: that
variable is unset on a first build and unchanged on a rebuild, so the answer
would once again depend on what started the build rather than on the state of
the repository.

What holds is a work queue whose state lives in GitLab: ask for the merged merge
requests that do not yet carry a processed marker, handle each, then mark it.
Processing becomes idempotent instead of depending on being run exactly once, so
it survives coalesced builds, replays, a restart and a wiped `jenkins-home`
alike. The full argument is in
[docs/docbot-queue-design.md](../docs/docbot-queue-design.md). Until
`process-queue` lands, `docbot update-manual` still handles only the merge that
produced HEAD, so this gap is open.

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
