# DocBot - does it need Jenkins?

**Status:** research, pre-decision. Written 2026-09-23. Verified against the `devinfra` stack
(GitLab **19.2.2 CE**, GitLab Runner 19.4, Docker executor) on the same day.
**Relationship to other documents:** challenges a **[DECIDED]** item in
[the foundation doc](mobimanual-docbot-foundation.md) under "Executor versus detector"
("Jenkins is the executor"), and restates the executor-facing parts of
[the queue design](docbot-queue-design.md) for GitLab CI.

Tags carry the same meanings as in the foundation doc, plus one:

- **[DOCS]** — taken from GitLab's current documentation and **not reproduced on the
  stack**. Only a few claims below still carry it. Everything the decision rests on was
  measured (see [What was verified](#what-was-verified)).

---

## The question

> The MobiVisor repo runs on GitLab and Jenkins. If DocBot only needs GitLab and can
> ditch Jenkins, that's better — fewer dependencies. But if dropping Jenkins makes
> DocBot significantly harder to build, keep it.

## Short answer

**DocBot does not need Jenkins, and dropping it makes DocBot easier to build, not
harder.** One condition applies, and it is not technical: the MobiVisor GitLab instance
needs a GitLab Runner that DocBot may use. If it has none and nobody will add one, keep
Jenkins. That is cheap too, because DocBot's design already reduces the executor to about
20 lines. **[PROPOSED]**

That second point matters most for the decision. Two standing decisions keep the executor
thin: "keep Jenkins thin" and the forge-side work queue. So this choice is **cheap to make
and cheap to reverse**. It does not deserve a long debate. It deserves one question to
whoever runs MobiVisor's GitLab (Q16 below).

---

## What Jenkins actually does for DocBot today

Every job Jenkins does for DocBot, next to the GitLab CI equivalent:

| Jenkins does | Where | GitLab CI equivalent | Harder, same, or easier |
|---|---|---|---|
| Receives a webhook when `main` moves | `gitlab-branch-source`, `manageWebHooks` | In-repo shape: a push to `main` *is* a pipeline, no webhook at all. Separate-project shape: one plain project webhook, branch-filtered to `main` **[EVIDENCE]** | **Easier.** Removes items 4 and 5 of the README's "Things that cost time to discover" and the `localhost` URL rejection |
| Runs `docbot` only on `main` | `when { branch 'main' }` | `rules: - if: $CI_COMMIT_BRANCH == "main"` **[EVIDENCE]** | Same |
| Serialises runs | `disableConcurrentBuilds()` | `resource_group: docbot`. Every waiting job still runs; none is coalesced **[EVIDENCE]** | Same |
| Hands the bot a GitLab token | JCasC credential + `withCredentials` | Masked, protected CI/CD variable | Same |
| Keeps artifacts (`detection.json`) | `archiveArtifacts` | `artifacts:` keyword | Same |
| Periodic safety net (queue design, step 7) | `cron` trigger | Pipeline schedule **[EVIDENCE]** | Same |
| Runs the bot in a pinned image carrying Node, Grunt, Pandoc, ImageMagick, pngquant | *Not done yet.* The queue design deferred it because in Jenkins it "costs the docker plugin, a socket mount and a registry" | `image: registry/docbot:x.y.z`. Every job already runs in an image of its choosing **[EVIDENCE]**; GitLab CE ships a container registry | **Easier.** This is the production packaging the foundation doc wants, and in GitLab CI it is the default rather than an add-on |
| Advisory comment on an open MR (delivery model A) | `when { changeRequest() }`, `CHANGE_ID` | `merge_request_event` pipelines with `CI_MERGE_REQUEST_IID`, or an MR webhook whose payload carries `object_attributes.iid` and `action` **[DOCS]** | Same |
| Posts a commit status on the MR | Plugin does it unasked | Not needed. The README already notes it "says nothing about the bot" | — |

Nothing on the Jenkins side lacks an equivalent. The one thing GitLab CI cannot do is the
same thing Jenkins cannot do: attach merge-request identity to a push to `main`.
`CI_MERGE_REQUEST_IID` is unset on the `main` pipeline, just as `CHANGE_ID` is on the
`main` build. **[EVIDENCE]** Either way the answer is the queue design's `process-queue`
and `resolve`, which are **executor-independent** because they read state from the forge,
not from the build (standing principle 7).

### What gets harder

Two things, both small:

1. **The CI job token cannot do DocBot's writes.** On the stack, `CI_JOB_TOKEN` got
   **HTTP 401** for `add_labels` and for creating a note, even on an existing merge
   request. It *did* succeed at everything DocBot reads: `commits/:sha/merge_requests`
   resolved the right merge request, and the merged-MR list returned 200.
   **[EVIDENCE]** The fine-grained job-token permissions (GA in 18.3) add read-only MR
   access and nothing more. **[DOCS]** DocBot therefore still needs a real token,
   exactly as it does under Jenkins. The natural choice is a **project access token**. It
   creates a bot user, and on self-managed GitLab it is available on every tier.
   **[DOCS]** That also answers queue-design **Q13** ("is the bot a GitLab account of its
   own?") for free. Note: on GitLab.com it needs Premium.
2. **Someone has to run a runner.** In `devinfra` that means a `gitlab/gitlab-runner`
   container with the Docker socket mounted and `network_mode` on `mobimanual-docbot`.
   Creating it took one `POST /user/runners` with the **existing** `api`-scoped seed
   token, which returns a `glrt-` token, then one non-interactive `gitlab-runner
   register`. Job containers resolved `gitlab.orb.local` with no further setup.
   **[EVIDENCE]** This replaces the Jenkins container. It does not add to it.

### What the prototype sheds

Of the seven hard-won items in the `devinfra` README ("Things that cost time to discover"
plus the `*.orb.local` section), the Jenkins-specific ones disappear: the JCasC symbol
names, the `manageWebHooks` + `afterSave()` registration trap, the `webHookMode: ITEM`
credential trap and the `localhost` URL rejection. Also gone: the Jenkins image and
`plugins.txt`, `casc/`, `jenkins-groovy.sh`, and about 750 MB of controller RSS
**[EVIDENCE]**, per the README's resource table. The GitLab-side items (the lying
healthcheck, `gitlab-rails runner` needing `-i`, local-network webhooks) stay.

---

## A finding the Jenkins-only framing hides: GitLab CI coalesces too

The queue design says Jenkins' build coalescing "stops being a bug" once the queue is
derived from the forge. The obvious hope is that GitLab CI avoids coalescing entirely,
since every push to `main` creates its own pipeline. **It does not avoid it.**

`workflow:auto_cancel:on_new_commit` defaults to `conservative`: when a new commit lands
on a branch, GitLab cancels older pipelines on that branch **unless one of their jobs
with `interruptible: false` has already started**. **[DOCS]** Reproduced on the stack
with an in-repo `.gitlab-ci.yml` on default settings, one runner and three merges one
second apart: **[EVIDENCE]**

```
  merged !1 -> 66063a62 at 11:12:52      pipeline 55  66063a62  success
  merged !2 -> 2be6793d at 11:12:54      pipeline 56  2be6793d  canceled
  merged !3 -> 6bbcca29 at 11:12:55      pipeline 57  6bbcca29  success
```

**Merge request !2 was never any running job's `HEAD`.** Pipeline 55 was already running
and survived. Pipeline 56 was still pending, so pipeline 57 cancelled it. That is the
Jenkins defect again, under a different name, and GitLab CI inherits it.

The same burst with `workflow: auto_cancel: on_new_commit: none` and
`resource_group: docbot` gave three pipelines, all successful, and their jobs ran strictly
one after another (09:15:41–09:16:04, 09:16:07–09:16:30, 09:16:33–09:16:56 UTC).
**[EVIDENCE]**

Two consequences:

- **The queue design is not Jenkins-specific. It is necessary on either executor.** This
  strengthens its case. Do not read "GitLab CI makes one pipeline per merge" as a reason
  to skip it.
- Set `auto_cancel: on_new_commit: none` plus `resource_group` anyway. It costs nothing,
  and it makes the "one pipeline per merge" intuition true. It cannot replace the queue:
  a dropped webhook, a failed pipeline or a runner outage still leaves a merge
  unprocessed, and only the forge-side query finds it again.

---

## Where the pipeline lives

If Jenkins goes, the next decision is where DocBot's pipeline definition sits.

| Option | Shape | Verdict |
|---|---|---|
| **A. `.gitlab-ci.yml` in the MobiVisor repo** | Push to `main` → pipeline → `docbot process-queue` | **Rejected as the default.** It is the simplest shape, but it switches GitLab CI on for a repository whose CI is Jenkins. MRs and commits start showing a second pipeline, it interacts with "Pipelines must succeed" if that is enabled, and the file that decides when DocBot runs becomes editable by the MRs DocBot reviews. The foundation doc rejects that last property for the bot itself |
| **B. Separate `docbot` project, triggered by webhook** | MobiVisor project webhook (push events, branch filter `main`) → `POST /projects/<docbot>/ref/main/trigger/pipeline?token=…` → pipeline in the `docbot` project runs `process-queue` against MobiVisor via the API. Plus an hourly pipeline schedule in the same project | **Chosen. [PROPOSED]**, and built end to end on the stack **[EVIDENCE]** |
| **C. Keep Jenkins** | As today | **The fallback if Q16 comes back "no runners".** Not a bad outcome: the executor is thin by design |

What option B did on the stack: **[EVIDENCE]**

- Three merges one second apart produced **three** `source=trigger` pipelines in the
  `docbot` project, and all three succeeded. With the default `auto_cancel`, none was
  cancelled: every triggered pipeline runs at the same `docbot` commit, so no "new
  commit" is there to cancel on. This closes an item the first draft of this document
  left **[UNKNOWN]**.
- `$TRIGGER_PAYLOAD` held the push event, and each pipeline got its own merge commit:
  `6301ed85`, `d210e07e`, `8ca86f62`.
- The feature-branch pushes that preceded the merges created **no** pipelines, so the
  webhook's `main` branch filter works.
- A pipeline schedule ran the same job (`source=schedule`, no payload).

Why B:

- **The MobiVisor repo carries nothing.** Its footprint is one project webhook. That is
  the same footprint Jenkins has today, so it cannot be a bigger ask of the MobiVisor
  team than the status quo.
- **Bot, pipeline and schedule sit together, outside the reviewed repo.** This extends
  the foundation doc's "a bot that reviews a repository should not be editable by the
  merge requests it reviews" to the pipeline itself.
- **The `docbot` project can build and host its own image** in GitLab's built-in
  registry, which settles the packaging question the queue design deferred.
- **The trigger carries no information, and that is deliberate.** The payload is there,
  but `process-queue` ignores it. The trigger means "drain now", the schedule means
  "drain anyway", and both run the same command. This is the queue design's "a second
  trigger, not a second code path".
- Delivery model A (advisory comment on the open MR) fits the same way: add MR events to
  the webhook, and a job reads `object_attributes.iid` from `$TRIGGER_PAYLOAD`. **[DOCS]**
  This part was not exercised.

Costs of B, stated plainly:

- The trigger token (`glptt-…`) sits in the webhook URL. Only maintainers of the
  MobiVisor project can see webhook config, which is the same exposure Jenkins' webhook
  secret has today.
- GitLab disables a failing webhook temporarily after 4 consecutive failures and
  permanently after 40. On self-managed, auto-disable for project webhooks has been off
  by default since 15.10. **[DOCS]** The hourly schedule is what makes this survivable,
  so the schedule is mandatory, not optional.
- A job token from the `docbot` project reading the MobiVisor project was not tested.
  It does not matter: DocBot's writes need the project access token anyway (see
  [What gets harder](#what-gets-harder)), so that token does the reads too.

A sketch, to show the size of the thing. **[PROPOSED]**. The `workflow`, trigger,
schedule and `resource_group` parts match what ran on the stack; `docbot process-queue`
does not exist yet:

```yaml
# docbot project: .gitlab-ci.yml
workflow:
  auto_cancel:
    on_new_commit: none
  rules:
    - if: $CI_PIPELINE_SOURCE == "trigger"    # MobiVisor webhook
    - if: $CI_PIPELINE_SOURCE == "schedule"   # hourly safety net
    - if: $CI_PIPELINE_SOURCE == "push"       # docbot's own build/test

process-queue:
  image: $CI_REGISTRY_IMAGE:$DOCBOT_VERSION
  resource_group: docbot
  rules:
    - if: $CI_PIPELINE_SOURCE =~ /^(trigger|schedule)$/
  script:
    - docbot process-queue --project "$MOBIVISOR_PROJECT" --out processed.json
  artifacts:
    when: always
    paths: [processed.json]
# FORGE_TOKEN: project access token on the MobiVisor project, masked + protected CI/CD variable
```

---

## Decision this would change

The foundation doc's "Jenkins is the executor **[DECIDED]**" was established in a
prototype that *started* from Jenkins, because the real repo uses it. Nothing in the
prototype tested whether Jenkins was needed. This document argues it is not, and asks
for the item to be reopened as:

> **The executor is whatever the MobiVisor GitLab can run. GitLab CI (option B) if a
> runner is available to DocBot, Jenkins otherwise. DocBot's code must not care which.**

The last sentence is already true of the design and should become a tested property:
`process-queue` should run unchanged from a laptop, from Jenkins and from GitLab CI.

---

## What was verified

Run on 2026-09-23 against the live stack, in two throwaway projects (`root/ci-spike`,
`root/docbot-spike`) and one runner container. `mobivisor-console` and Jenkins were not
touched. Everything was removed afterwards: projects permanently deleted, runner
unregistered, container, volumes and runner images removed.

| # | Check | Result |
|---|---|---|
| 1 | Runner via `POST /user/runners` + non-interactive `register`, Docker executor on `mobimanual-docbot` | Online in seconds; the existing `api`-scoped seed token was enough; job containers resolved `gitlab.orb.local` |
| 2 | Three merges, in-repo `.gitlab-ci.yml`, default `auto_cancel` | **Middle pipeline cancelled.** GitLab CI coalesces too |
| 3 | Same burst, `auto_cancel: none` + `resource_group` | Three pipelines, run strictly one after another |
| 4 | `CI_JOB_TOKEN` writes and reads | `add_labels` 401, create note 401; commit→MR resolution 200 and correct, merged-MR list 200 |
| 5 | Option B: push webhook (filter `main`) → trigger API of a second project | One `trigger` pipeline per merge, none cancelled, `$TRIGGER_PAYLOAD` carries each merge commit, feature-branch pushes filtered out |
| 6 | Pipeline schedule on the second project | Runs the same job, `source=schedule` |

Incidental findings, for whoever ports `devinfra`:

- **The push→create race the queue design recorded bit again.** Creating a merge request
  immediately after pushing its branch failed for two of three branches, with no
  throttling involved. Any script that opens merge requests must retry the create.
- **GitLab 19 deletes projects lazily.** `DELETE /projects/:id` only marks the project
  for deletion and renames it `…-deletion_scheduled-<id>`. Immediate removal takes a
  second call with `permanently_remove=true&full_path=<renamed path>`. `seed-project.sh`
  already polls for deletion, but it waits on the *original* path, which frees up at
  once because of the rename. So re-seeding still works, but each re-seed leaves the old
  project behind (with its Jenkins webhook) until the deletion delay passes. This was
  inferred from the rename and not tested against `seed-project.sh`.

Porting `devinfra` itself (runner instead of Jenkins in compose, `seed-project.sh`
creating the `docbot` project, trigger, webhook and schedule, `open-test-mr.sh` polling
the pipelines API) is roughly a day's work, and most of it is deletion.

---

## New open questions

| # | Question | Blocks |
|---|---|---|
| 16 | **Does the MobiVisor GitLab have a runner DocBot may use, or may one be added?** Is it self-managed or GitLab.com (compute-minute quotas, and project access tokens need Premium on .com)? **And is Auto DevOps enabled there?** GitLab 19.2.2 ships with it on instance-wide **[EVIDENCE]**, from `devinfra` on 2026-09-23: every push to a project without a `.gitlab-ci.yml` created a build/test/scan pipeline that sat "stuck" for want of a runner. It was harmless only *because* there was no runner. Adding a runner for option B would make those pipelines start running on every MobiVisor push, unless Auto DevOps is off for that project first. `devinfra` now disables it in `seed-gitlab.sh` | The whole choice. "No" means option C, keep Jenkins |
| 17 | Who owns the MobiVisor project's webhook config? Adding one webhook is the only change option B asks of that project | Option B |
| 18 | Is "Pipelines must succeed" enabled on the MobiVisor project? | Only option A, which is rejected, but it confirms the rejection |
