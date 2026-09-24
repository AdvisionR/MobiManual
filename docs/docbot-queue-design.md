# DocBot — the work queue and the CLI it forces

**Status:** design, pre-implementation. Written 2026-09-10 against the running `devinfra` stack.
**Relationship to other documents:** this refines [the foundation doc](mobimanual-docbot-foundation.md)
under "The coalescing gap and the work queue", and replaces item 1 of the roadmap in
[current-state.md](current-state.md) with something implementable. Tags carry the same
meanings as in the foundation doc: **[DECIDED]**, **[EVIDENCE]**, **[PROPOSED]**, **[UNKNOWN]**.

---

## The question this answers

> Is implementing the queue the next logical step?

Yes — and it is the *only* unblocked step, which is a stronger reason than "logical
next". But the framing needs two corrections before it is buildable.

### Correction 1 — the queue is not a step you can take in the current codebase

`devinfra/jenkins/docbot` is a 120-line POSIX shell script. The queue needs paginated
list queries, client-side date filtering, per-item error isolation, idempotency lookups,
label and note writes, and a structured artifact per item. That is writable in shell and
should not be written in shell.

So the real step is: **replace the stub with the CLI the foundation doc already
specified, whose first subcommand is `process-queue`.** The queue is the forcing
function for the CLI, not a feature added to a script. This is not new design — the CLI
shape is already **[DECIDED]** — it is cashing in a decision that has been sitting
unexercised.

### Correction 2 — a queue with a stub payload cannot be validated

"Drained three merge requests correctly" and "drained three merge requests into a no-op"
produce identical logs when the payload is `echo "(stub: a real DocBot would decide
something)"`. The queue must land with the thinnest *real* payload, and there is exactly
one candidate that needs no model, no governance sign-off and no unanswered question:
**the tier-1 deterministic gate.**

Each makes the other testable. The gate gives the queue an observable result per item;
the queue gives the gate the only input it has ever lacked. **[PROPOSED]**

### Why now, and not something else

Every other line of work is blocked on someone else's answer:

| Work | Blocked on |
|---|---|
| Model tier of the gate; drafting agent | Q10, data-governance sign-off — a legal-calendar item |
| Screenshot staleness | Q2, which E2E framework replaces Protractor |
| `generated` reference tables | Q3 and Q8, where the policy schemas live and whether the tables exist |
| Fixing the manual's heading/numbering defects | Q11, write access to the real repository |
| Drafting in one language or three | Q1 |

The queue, the tier-1 gate and the CLI skeleton depend on none of these. They run against
`doc-map.json` and the fixture stack, both of which exist today. **[EVIDENCE]**

Start the Q10 clock in parallel today — it is the long pole for everything after this
step, and it costs nothing to begin.

---

## The bug, reproduced

Before designing the fix, the defect was confirmed end to end on the running stack rather
than inferred from Jenkins' documentation. **[EVIDENCE]**

Two merge requests touching different files were merged one second apart:

```
  !3  src/enrollment/ios/EnrollmentWizard.tsx   merged 15:11:52
  !4  src/console/settings/LdapSettings.tsx     merged 15:11:53
```

Jenkins ran **one** `main` build. Its `detection.json`:

```json
{ "mr": "4", "files": ["src/console/settings/LdapSettings.tsx"] }
```

**Merge request !3 was never seen by any build.** No error, no artifact, no failed stage —
the build went green. Had !3 been the merge that changed a documented enrollment flow, the
manual would now be wrong and nothing anywhere would say so.

This is worth having measured, for two reasons. It converts the foundation doc's
"one build can cover several merges" from a plausible claim into a demonstrated one, and
it fixes the shape of the regression test: **merge two merge requests one second apart and
assert both end up labelled.** That test does not exist yet, and until it passes nothing
below is demonstrated.

One incidental finding from the attempt: a third merge in the same burst was **refused**
by GitLab, not queued. Mergeability is recomputed after `main` moves, and a merge request
whose `merge_status` predates the move is rejected. The burst script has to re-poll
`merge_status` between merges or it will silently test two merges when it meant to test
three.

---

## What was verified today

With the defect confirmed, the API the fix depends on was measured on the same stack —
GitLab **19.2.2 CE**, 2026-09-10. Every design decision below rests on this table.
**[EVIDENCE]**

| # | Assumption | Result |
|---|---|---|
| 1 | The merge-request **list** representation carries what the queue needs | Confirmed: `merged_at`, `labels`, `merge_commit_sha`, `squash_commit_sha`, `sha`, `target_branch`, `author`, `web_url` are all present on the list response |
| 2 | `not[labels]` filters server-side | Works. `not[labels]=a,b` excludes a merge request carrying **any** of the listed labels — verified with a discriminating case (an MR holding one of two listed labels was excluded) |
| 3 | `order_by=merged_at` is a valid ordering | Yes. `order_by=bogus_field` returns HTTP 400 "order_by does not have a valid value"; `merged_at` returns 200 |
| 4 | `PUT ?add_labels=` is additive and tolerates a missing label | Both. It auto-creates the project label — with default colour `#6699cc` and no description |
| 5 | `updated_after` can stand in for a `merged_at` floor | **No.** Applying a label bumps `updated_at` and not `merged_at`. It is a safe *superset* bound only |
| 6 | Notes can carry a machine-readable record | Yes, and `system: true/false` cleanly separates GitLab's own notes from the bot's |
| 7 | Pagination is introspectable | `X-Total`, `X-Total-Pages`, `X-Next-Page`, `X-Per-Page` all returned |
| 8 | Rapid merge-request creation is rate-limited | Not in this instance: `merge_request_create_limit` unset, `throttle_authenticated_api_enabled` false, `notes_create_limit` 300. An early failure that looked like throttling was a push→create race in the test harness, not a limit |

**The most useful of these is #1.** Discovery is a single list call, not a list call plus
one fetch per candidate. Only merge requests that survive the filter need
`/merge_requests/:iid/changes`, so cost scales with the backlog, not with repository
history.

**#5 is the one that would have caused a bug.** The obvious way to bound the query is
`updated_after=<epoch>`, and it is wrong on its own: relabelling an old merge request
pulls it back over the line. Bound with `updated_after` if you like, but decide with
`merged_at`.

### One finding that was not an assumption

**The seeded GitLab project predates Phase 0.** The project in the running stack still
carries the pre-refactor fixture — `src/**.tsx`, `docs/pages/`, `manual.yaml` — while
`devinfra/demo-repo/` was rebased onto the real MobiVisor shape in commit 7b5fba8.
Phase 0 was done in git and never re-seeded into the stack. Anyone testing the gate
against this stack today would be testing it against the layout Phase 0 removed.
**Re-seed before step 2.** **[EVIDENCE]**

---

## Architecture

### The seam that matters

```
docbot process-queue          knows GitLab. knows nothing about documentation.
      │   discovery, ordering, marking, failure isolation
      │
      ├── docbot gate         pure function. no network. no clock.
      │       (changed_files, doc-map.json) -> verdict.json
      │
      └── docbot report       knows GitLab. knows nothing about gating.
              verdict.json -> a note, a label, a ledger record, an MR
```

**`gate` must not touch the network.** That single constraint buys three things:

1. The evaluation harness is free — replay a corpus of historical merge requests through
   `gate` offline and score the verdicts, which the foundation doc names as the real
   research output of the pilot.
2. The gate is unit-testable with no fixture stack, no webhook and no wait.
3. The gate can be run by a developer on a laptop against a local checkout, which is the
   loop that prompt and rule work actually rewards.

If `gate` is allowed to fetch its own diff "for convenience", all three are lost. It is
the highest-value boundary in the design and the easiest one to erode. **[DECIDED]**

### The control loop

```
docbot process-queue
  1. GET /projects/:id/merge_requests
         ?state=merged
         &target_branch=main
         &not[labels]=docbot-processed,docbot-failed
         &order_by=merged_at&sort=asc
         &updated_after=<epoch>          # bound only; see verified assumption #5
         &per_page=100                   # follow X-Next-Page
  2. drop merged_at < DOCBOT_EPOCH       # the real floor
  3. drop merge requests labelled docbot-generated      # loop cut, at source
  4. cap at --max (default 25), loudly
  5. for each, oldest first:
       a. GET /merge_requests/:iid/changes     -> context
       b. docbot gate                          -> verdict
       c. docbot report                        -> note + ledger record + docs MR
       d. label: docbot-processed + the verdict label
  6. write processed.json
```

Step 5 is act-then-mark, deliberately. See [Marking](#marking-act-then-mark).

### Jenkins' coalescing stops being a bug

Once the queue is derived rather than received, build coalescing is no longer a defect to
work around — it is an optimisation. Two merges landing during one build fold into one
pending build, which then drains both. Fewer builds, same outcome. That inversion is the
whole point of standing principle 7, and it is worth stating out loud because the
prototype's documentation currently presents coalescing as a hazard.

The same property makes the periodic safety net nearly free. The `devinfra` README, under
"Deliberately not here", notes that discovery is webhook-only, so a dropped delivery means a merge request is
never seen. With a derived queue, the fix is a `cron` trigger on the same job running the
same command, which finds nothing on almost every run. **A second trigger, not a second
code path.** **[PROPOSED]**

---

## Design decisions

### Marking: label for the query, note for the record

The foundation doc left this as "a label, or a note". They do different jobs and the
answer is both.

| Mechanism | Queryable server-side | Carries structure | Verdict |
|---|---|---|---|
| Label | Yes — verified assumption #2 | No | **The queue marker** |
| Note | No; it would be one fetch per merge request, forever | Yes | **The verdict record** |
| Jenkins artifact or a file in the repo | — | Yes | **Rejected** — violates standing principle 7; does not survive a wiped controller |

So: the label answers *is this done*, in one list call. The note carries the verdict JSON
that satisfies "log every verdict from day one". **[PROPOSED]**

Labels to seed deliberately in `seed-project.sh` rather than let `add_labels` invent —
verified assumption #4 means an unseeded label appears with a default colour and no
description, which is a bot writing undocumented state into a shared namespace:

| Label | Applied by | Job |
|---|---|---|
| `docbot-processed` | always, last | The queue marker. Its only consumer is the query |
| `docbot-impact` / `docbot-no-impact` / `docbot-undecidable` | per verdict | Human-visible signal. A reviewer filters the merge request list by `docbot-no-impact` and eyeballs for false negatives — this is the pilot's research workflow |
| `docbot-failed` | on per-item failure | Removed by a human to re-queue |
| `docbot-generated` | on the bot's own merge requests | Loop cut. Already in the stub |

Keeping `docbot-processed` separate from the verdict labels is deliberate: the queue query
names one label whose meaning never changes. Folding the two together — querying
`not[labels]=docbot-impact,docbot-no-impact,...` — works until someone adds a verdict class
and forgets the query, at which point the queue loops forever on those items. One label,
one job. **[PROPOSED]**

### Marking: act, then mark

The marker write can fail after the work is done. The ordering is therefore a choice
between two failure modes, and they are not symmetric:

| Order | Failure mode | Verdict |
|---|---|---|
| Mark, then act | The action fails; the merge request is marked done and is **never seen again**. Silent documentation loss | **Rejected.** This is the exact bug the queue exists to fix, reintroduced |
| Act, then mark | The mark fails; the action repeats on the next run | **Chosen** |

At-least-once, not at-most-once. That forces every action to be idempotent, which is a
discipline worth having regardless. **[DECIDED]**

Idempotency needs a key, and the source merge request iid is a good one because everything
the bot creates can be named from it deterministically:

- branch `docbot/mr-<iid>`
- ledger record `doc-impact/pending/mr-<iid>.json`
- the verdict note, tagged `<!-- docbot:verdict v1 mr=<iid> -->`

"Have I already done this?" then becomes a lookup, not a search. Before opening a docs
merge request, check whether `docbot/mr-<iid>` exists. **[PROPOSED]**

### The epoch floor, and the cold start

Not covered by the foundation doc, and it bites on day one: on the first run, *every*
merge request ever merged into `main` lacks the `docbot-processed` label. Without a
floor, the first drain attempts the entire history of the repository.

| Option | Verdict |
|---|---|
| Backfill `docbot-processed` across all historical merge requests once, at deployment | Rejected as the primary mechanism — thousands of writes, and it leaves no record of *why* the cutover is where it is |
| A configured `DOCBOT_EPOCH`; ignore anything merged before it | **Chosen.** One config line, self-documenting, and it bounds the query permanently so "the query is the queue" stays cheap forever |

Pair it with `--max` (default 25) as a runaway guard: if the epoch is ever misconfigured,
the symptom is a loud message about a capped drain, not a build that opens two hundred
merge requests. **[PROPOSED]**

### Failure isolation

If merge request 5 fails, does the drain stop or continue to 6?

Neither, uniformly. The stub already distinguishes two classes of HTTP failure and refuses
to collapse them; extend that discipline to the drain:

| Failure | Response | Why |
|---|---|---|
| **Infrastructure** — 401, 5xx, network, GitLab unreachable | **Stop the drain. Fail the build red.** | The next item will fail the same way. Nothing is learned by continuing, and a red build is a *visible* signal — silence was the enemy here, not stopping |
| **Per-item** — the gate raised on this diff, a malformed doc-map entry | **Label `docbot-failed`, continue to the next item** | One bad merge request must not block every later documentation update. It leaves the queue, so it does not retry forever, and it appears in a list a human can filter for |

Re-queueing a failed item is a human removing the label. That is deliberate: in an R&D
pilot you want to look at the failure before it is retried. **[PROPOSED]**

Ordering is preserved by `order_by=merged_at&sort=asc` — verified assumption #3, so no
client-side sort. Break ties on `iid` ascending; two merges in the same second are common
in a burst and the API gives no guarantee within a tie.

### Concurrency

`disableConcurrentBuilds()` is already in the Jenkinsfile and covers same-job overlap,
including the merge-triggered and `cron`-triggered runs **provided they are the same
job**. Keep them so.

No lockable resource. The real protection is that act-then-mark plus idempotent actions
make a double drain wasteful rather than wrong — and a design whose correctness depends
on a lock is a design that breaks the first time someone runs the CLI on a laptop against
the real forge. **[PROPOSED]**

### What HEAD-resolution becomes

The existing commit→merge-request resolution does not get deleted. It stops being the
entry point and becomes `docbot resolve`: a diagnostic, and a consistency assertion.

If `HEAD` is a merge commit whose merge request is *not* in the queue and *not* already
marked, something is wrong — a mislabelled item, a misconfigured epoch, a clock problem.
That is worth logging. The careful 200/404/other handling in the stub took effort to get
right and is still correct; it is answering a different question than the queue does.
**[PROPOSED]**

---

## The gate, in the shape the queue needs

Tier 1 only. No model. Pure function of the changed-file list and `doc-map.json`.

### Three-valued, not boolean

```json
{
  "schema": "docbot.verdict/1",
  "mr": { "iid": 12, "url": "...", "merged_at": "2026-09-10T13:22:04Z" },
  "tier": 1,
  "decision": "doc-impact | no-doc-impact | undecidable",
  "areas": [
    { "id": "kiosk-modes", "class": "ai-drafted",
      "pages": ["_policies_kiosk.md"],
      "matched": ["public/app/policies/kiosk/kiosk.controller.js"],
      "already_served": false }
  ],
  "pages": { "en": ["_policies_kiosk.md"], "tr": [...], "de": [...] },
  "unmapped": ["public/app/reports/export-schedule.controller.js"],
  "reason": "..."
}
```

**`undecidable` is the important one.** A changed path matching no doc-map area is a
question tier 1 genuinely cannot answer, and collapsing it into `no-doc-impact` is
precisely how documentation goes missing without anyone noticing. It is what tier 2 exists
for; until tier 2 exists, it routes to a human. The fixture's `unmapped` kind already
exists to test this. **[PROPOSED]**

Precedence when one merge request touches several areas: `doc-impact` > `undecidable` >
`no-doc-impact`. Report `unmapped` paths regardless of the decision — an MR can both
clearly affect the kiosk page and touch something nobody has classified.

Match every area, not first-match-wins. Regexes in `doc-map.json` overlap by design, and
first-match-wins makes the verdict depend on file order in a JSON document.

### One refinement worth having on day one

**If every page an area points to was itself modified in the same merge request, that area
is already served** — downgrade it. A developer who updates the kiosk controller and the
kiosk page in one merge request should not be told the kiosk page needs attention.

Deterministic, cheap, and it removes a whole class of false positive that would otherwise
teach reviewers to ignore the bot in its first week. The fixture already carries a `both`
kind for exactly this case. **[PROPOSED]**

### The test matrix already exists

`open-test-mr.sh` enumerates ten kinds against their expected gate behaviour. That table
*is* the gate's unit-test matrix — the same cases, run as a pure function against fixture
file lists, with no stack running. Write them as `pytest` parameters and the fixture
script becomes the integration-level echo of the same table rather than the only place it
is checked.

---

## Implementation language

**Python.** The foundation doc marked this **[PROPOSED]** and blocked on Q3 — where the
policy schemas live.

**Q3 does not block it.** Q3 gates `render-reference` and nothing else. It has no bearing
on the queue, the gate, the reporter or the drafting loop. And the foundation doc's own
recommendation for the awkward branch — export JSON Schema as a console build step —
keeps DocBot in Python anyway.

**Decide Python now** and let Q3 gate only the subcommand it actually gates. `typer` for
the CLI, `httpx` for GitLab, `pytest` for the eval harness. **[PROPOSED — decision
requested]**

---

## What changes in the repository

The bot is currently a file inside the fixture infrastructure. It is the product; the
fixture is scaffolding. Separate them:

```
docbot/                      # the product
  pyproject.toml
  src/docbot/
    cli.py                   # typer entry point
    forge/gitlab.py          # the only module that knows GitLab exists
    queue.py                 # process-queue
    gate.py                  # pure. no imports from forge/
    report.py
    models.py                # verdict schema
  tests/
    test_gate.py             # the open-test-mr.sh kind table, as parameters
    test_queue.py            # against a recorded forge, not the live one
devinfra/
  jenkins/Dockerfile         # pip-installs docbot/ instead of COPYing a shell script
  jenkins/docbot             # deleted
  scripts/open-test-mrs.sh   # new: the burst test
```

Keeping `gate.py` unable to import `forge/` is the seam from
[Architecture](#the-seam-that-matters), enforced by a lint rule rather than by good
intentions.

**Packaging, for the prototype:** install the package into the Jenkins controller image,
as today. The production shape in the foundation doc is a pinned `docbot:x.y.z` image the
Jenkinsfile runs as an agent, carrying Node, Grunt, Pandoc, ImageMagick and pngquant for
the validation gates. `devinfra` has no registry and no agents — jobs run on the
controller — so adopting that now costs the docker plugin, a socket mount and a
registry, and buys nothing this step needs. **Record it as a knowing divergence, not a
decision.** **[PROPOSED]**

---

## The first thing DocBot writes should be a fact, not a draft

The fixture already carries `doc-impact/` with a README describing a ledger record per
merged merge request, written on branch `docbot/mr-<iid>` and opened as a merge request.
That is the right first payload, and the reason is worth stating:

**It exercises the entire write path — branch, commit, merge request, `docbot-generated`
label, link back to the source — with content that is derived rather than generated, so it
cannot be wrong in an interesting way.** If the write path is broken, you find out on
content whose correctness is not in question. Every later step reuses that path and
changes only the payload.

It is also delivery model C's content shipped through model B's mechanism, which is what
the foundation doc means by "B detects, C writes" — reached earlier than expected,
because the ledger record needs no model.

---

## Sequenced steps

| # | Step | Depends on | Rough size |
|---|---|---|---|
| 1 | Re-seed the stack from the post-Phase-0 `demo-repo/` | — | An hour. Do it first; everything below tests against it |
| 2 | `docbot/` package, `typer` skeleton, `resolve` ported from the stub, Dockerfile installs it | 1 | Half a day |
| 3 | `docbot gate` — pure, three-valued, the `already_served` refinement, the kind table as `pytest` parameters | 2 | A day or two. **No stack needed** |
| 4 | `docbot process-queue` — the loop, labels, notes, epoch, `--max`, failure isolation | 2, 3 | Two days |
| 5 | `open-test-mrs.sh` — the burst test reproduced above, re-polling `merge_status` between merges. Assert every merged MR ends labelled | 4 | Half a day |
| 6 | `docbot report` — the ledger record on `docbot/mr-<iid>`, `docbot-generated` label, link back | 4 | A day or two |
| 7 | `cron` trigger on the same job as the safety net | 4 | Minutes |

Steps 3 and 4 are independent once 2 lands and can be built in either order or in
parallel. Step 5 is the regression test for the bug this whole design exists to fix, and
nothing above it is demonstrated until it passes.

**In parallel, on someone else's calendar:** start Q10 (governance sign-off), and get
answers to Q1, Q2, Q3, Q5 and Q11. Step 8 is the model tier, and it cannot start until
Q10 lands.

---

## New open questions

| # | Question | Blocks |
|---|---|---|
| 12 | What is `DOCBOT_EPOCH` for the real repository — the pilot start date, or a release tag? | Step 4 |
| 13 | Is the bot a GitLab account of its own, or does it act as a human's token? Labels, notes and merge requests all carry an author, and "root did this" makes the verdict log unreadable | Step 4; it also decides whether `docbot-generated` is even needed, since the author would identify the bot |
| 14 | Should the ledger record merge request be one per source merge request, or one accumulating branch per release? The `doc-impact/README.md` implies per-merge-request; model C implies accumulation | Step 6 |
| 15 | Does the real project already use labels whose namespace `docbot-*` would collide with? | Step 1 |

Question 13 is the one worth answering early. It is cheap to arrange up front and
expensive to retrofit — every note and label written before the switch carries the wrong
author, and the verdict log is the pilot's deliverable.
