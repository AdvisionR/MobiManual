# DocBot — the CLI: where it lives and how it is invoked

**Status:** design, pre-implementation. Written 2026-09-23 against the running `devinfra` stack.
**Relationship to other documents:** [the foundation doc](mobimanual-docbot-foundation.md)
fixed the CLI's *shape* ("CLI shape", "Keep Jenkins thin") and
[the queue design](docbot-queue-design.md) fixed its *first command* and module layout
("What changes in the repository"). This document settles what both left open: the name,
where the code lives, how it is packaged, how it is configured, its input/output
contract, and what running it looks like in each place it runs. It is written to hold
whichever executor [the executor question](docbot-ci-executor.md) ends up choosing.

Tags as in the foundation doc: **[DECIDED]**, **[EVIDENCE]**, **[PROPOSED]**,
**[UNKNOWN]**, plus **[DOCS]** as defined in the executor doc: taken from upstream
documentation, not yet reproduced here.

---

## The question

> How would the MobiManual CLI look? Where would it live, how would it be invoked?

## Short answer

- **One executable, `docbot`.** It is a Python package in `docbot/` at the root of *this*
  repository, next to `devinfra/` and the design docs. **[PROPOSED]**
- **It never lives in the MobiVisor repository.** MobiVisor holds only facts about
  itself: `doc-map.json`, `htmlDocPages`, and the route table. DocBot's behaviour lives here.
- **It works through the GitLab API, not the working directory.** Tier 1 (queue, gate,
  report) needs no clone of MobiVisor at all. **[EVIDENCE]** for the API calls it rests on.
  Only the later commands that run `grunt` need a checkout.
- **The same command runs in three places:** the executor, a laptop, and the evaluation
  harness. In CI it is one line: `docbot process-queue > processed.json`.
- **stdout carries the JSON result, stderr carries the narration, and the exit code says
  which kind of thing happened.**

```
 this repository (MobiManual)                  MobiVisor GitLab project
 ├── docbot/    ──build──▶ docbot image  ─┐     ├── public/app/**   public/doc/**
 ├── devinfra/  (test stack)              │     ├── doc-map.json   ◀── read at the merge commit
 └── *.md       (design)                  │     └── no DocBot code
                                          ▼
          executor — Jenkins today, maybe GitLab CI:   docbot process-queue
                                          │   GitLab API only
                                          ▼
          on MobiVisor:  labels · verdict notes · docbot/mr-<iid> merge requests
```

---

## What the stack says today

Checked on 2026-09-23 against GitLab 19.2.2 CE. **[EVIDENCE]**

| # | Check | Result | Consequence |
|---|---|---|---|
| 1 | Python in the Jenkins image | **Absent.** `python3: not found` on Debian 13 (trixie) | The packaging step has to add it. Trixie's `python3` is 3.13 **[DOCS]** |
| 2 | `GET /repository/files/doc-map.json/raw?ref=<merge sha>` | 200, 2,836 bytes | The doc map *as of the merge* is one API call, so the gate's second input needs no checkout |
| 3 | `GET /merge_requests/:iid/diffs` | 200. Paginated (`X-Per-Page: 20`, `X-Total`). Per file: `old_path`, `new_path`, `new_file`, `renamed_file`, `deleted_file` | This is the gate's first input, including renames. The stub's `/changes` still answers 200, but it is deprecated in favour of `/diffs` **[DOCS]**. Use `/diffs` |
| 4 | Host toolchain | Python 3.14 and `uv` present | The laptop path below works as written |
| 5 | **Is the stack re-seeded from the post-Phase-0 fixture?** | **No.** `main` still has `src/`, `docs/`, `tests/` and the old doc map (`^src/enrollment/ios/` and similar) | See below |

### Finding 5, stated plainly

The queue design's step 1 ("re-seed before anything else") has not happened. Today's test
merge request !9 did not touch an existing file. It **created**
`public/app/enrollment/ios/enrollment-wizard.controller.js` (`new_file: true`) inside the
old layout, because `open-test-mr.sh` creates any missing file it is asked to touch.
Detection reported it correctly, because detection never looks at the layout. A tier-1 gate
would have judged !9 `undecidable` against the seeded doc map. The local fixture says
`doc-impact`.

Two consequences:

- Re-seed before step 2 of the queue design, as that document already says.
- `open-test-mr.sh` should **fail** when a kind's file is missing rather than create it.
  Every kind's file exists in `demo-repo/`, so the create-if-missing branch has no
  legitimate use left. Its only effect is to hide a stale seed. **[PROPOSED]**

---

## Name: `docbot`

The request says "MobiManual CLI". The executable should still be called `docbot`.
**[PROPOSED — confirm, Q19]**

| Option | Verdict |
|---|---|
| `mobimanual` | **Rejected.** It is the project's name, and "the manual" is what the project produces. Everything the bot already writes or reads is named `docbot`: the Jenkinsfile call, the `docbot-*` labels, the `docbot/mr-<iid>` branches, the `<!-- docbot:verdict -->` note tag and the `DOCBOT_EPOCH` setting. Renaming the executable alone would leave one odd name out |
| `docbot` | **Chosen.** Matches every existing artifact and every design doc |

If you do want `mobimanual`, it costs one line (`[project.scripts]` in `pyproject.toml`).
This is not a decision worth defending hard. It is recorded so the choice is visible.

---

## Where the code lives

> **Superseded 2026-09-24.** This section never weighed how the code reaches the real
> repository. [docbot-code-location.md](docbot-code-location.md) does, and DocBot now
> lives at `tools/docbot/` inside the MobiVisor fixture while Jenkins is the executor.
> That document also replaces "Packaging" below. The layout keeps the shape shown here,
> under `tools/docbot/` instead of `docbot/`.

| Option | Verdict |
|---|---|
| **A. In the MobiVisor repo** (for example `tools/docbot/`) | **Rejected.** The foundation doc already rules that "a bot that reviews a repository should not be editable by the merge requests it reviews". It would also make every change to DocBot a MobiVisor merge request, which the gate would then judge, and tie DocBot's release cadence to the console's |
| **B. `docbot/` in this repository** | **Chosen. [PROPOSED]** This repository already *is* the DocBot project: the design docs, the fixture, and the test stack that exercises it. Under the executor doc's option B it becomes the `docbot` GitLab project that builds the image and owns the pipeline, with no move needed |
| **C. A repository of its own, just for the package** | **Rejected for now.** It separates the code from the fixture that tests it, even though both are driven by the same kind table: `open-test-mr.sh` for integration and `test_gate.py` for units. Revisit if a second team consumes the package |
| **D. Stay at `devinfra/jenkins/docbot`** | **Rejected.** The product would live inside the scaffolding, under a path that names one executor. The queue design already schedules this file for deletion |

### What stays in MobiVisor, and the rule behind it

One rule decides where any future setting goes:

- **Would it be wrong for a different repository?** Then it is a fact about the repository
  and lives *in* MobiVisor, versioned with the code it describes: `doc-map.json`,
  `htmlDocPages`, the route table.
- **Would it be wrong for a different deployment?** Then it is deployment config and comes
  from the environment: forge URL, token, epoch.
- **Neither?** Then it is code, in `docbot/`.

### Layout

This extends the queue design's tree. The additions are `config.py`, `resolve.py`, the
`Dockerfile` and `test_cli.py`.

```
docbot/
  pyproject.toml            # [project.scripts] docbot = "docbot.cli:app"; requires-python >= 3.12
  Dockerfile                # production image: docbot + Node, Grunt, Pandoc, ImageMagick, pngquant
  src/docbot/
    cli.py                  # typer. argument parsing and exit codes, nothing else
    config.py               # flag > env > default. the only module that reads os.environ
    forge/gitlab.py         # the only module that imports httpx
    queue.py                # process-queue
    gate.py                 # pure. cannot import forge/ (lint rule)
    report.py
    resolve.py              # the stub's HEAD -> merge request logic, ported
    models.py               # verdict/1, processed/1, resolution/1
  tests/
    test_gate.py            # the open-test-mr.sh kind table, as pytest parameters
    test_queue.py           # against a recorded forge, not the live one
    test_cli.py             # exit codes; nothing but one JSON document on stdout
```

Dependencies are `typer` and `httpx`, and nothing else until something needs it.

---

## Packaging

| Where | How | Status |
|---|---|---|
| Laptop | `uv run --project docbot docbot …` from the repository root, or `uv tool install -e ./docbot` for a `docbot` on `PATH` | **[PROPOSED]** |
| `devinfra` Jenkins | The Jenkins `Dockerfile` installs `python3` and `python3-venv`, then installs `docbot/` into a venv whose `bin/` is on `PATH`. The compose build context is `./jenkins`, which cannot see `../docbot`. Add it with `additional_contexts: { docbot: ../docbot }` and `COPY --from=docbot` rather than widening the context to the whole repository **[DOCS]** | **[PROPOSED]**. A knowing divergence from production, as in the queue design |
| Production | A pinned `docbot:x.y.z` image built from `docbot/Dockerfile`. The executor runs it as the job's image | **[PROPOSED]**, as in the foundation doc |

| Rejected | Why |
|---|---|
| Publish to an internal PyPI index | The validation gates need Node, Grunt and Pandoc anyway, so an image is needed regardless. A package index would be a second distribution channel for the same code |
| Single binary (PyInstaller or similar) | Same reason. It buys nothing an image does not already give, and costs a build step |
| Keep `COPY`ing a script, as today | Only works while the bot has no dependencies. `typer` and `httpx` end that |

---

## Invocation

### In CI

Jenkins, replacing the current stage:

```groovy
stage('DocBot') {
  when { branch 'main' }
  steps {
    withCredentials([string(credentialsId: 'docbot-gitlab-token', variable: 'DOCBOT_GITLAB_TOKEN')]) {
      script {
        def rc = sh(script: 'docbot process-queue > processed.json', returnStatus: true)
        if (rc == 3)      { unstable('some merge requests failed: filter by the docbot-failed label') }
        else if (rc != 0) { error("docbot exited ${rc}") }
      }
    }
    archiveArtifacts artifacts: 'processed.json', allowEmptyArchive: true
  }
}
```

`DOCBOT_GITLAB_URL`, `DOCBOT_PROJECT` and `DOCBOT_EPOCH` go in the job's environment. The
exit-code mapping is the only Groovy with any branching in it. It translates a code into a
build status and decides nothing, which keeps it inside "keep Jenkins thin".

`process-queue` ignores `HEAD`, so `when { branch 'main' }` is now only a trigger, and
the `cron` safety net runs the same line. Note that in the Jenkins shape this file lives in
the MobiVisor repository, where a merge request can change what command runs. That is a
known limit of the Jenkins shape and one more point for the executor doc's option B.

GitLab CI, in the executor doc's option B:

```yaml
process-queue:
  image: $CI_REGISTRY_IMAGE:$DOCBOT_VERSION
  resource_group: docbot
  script: docbot process-queue > processed.json
  allow_failure:
    exit_codes: [3]          # shows as a warning, not a pass: see "Exit codes"
  artifacts: { when: always, paths: [processed.json] }
```

### On a laptop, against the `devinfra` stack

```bash
export DOCBOT_GITLAB_URL=http://gitlab.orb.local
export DOCBOT_PROJECT=root/mobivisor-console
export DOCBOT_GITLAB_TOKEN=$(sed -n 's/^GITLAB_PAT=//p' devinfra/.runtime/gitlab.env)

uv run --project docbot docbot process-queue --dry-run        # what would a drain do? writes nothing
uv run --project docbot docbot resolve e20d69c4               # which merge request produced this commit?

# the gate is pure, so no stack is needed at all:
git -C ../mobivisor diff --name-status main~1 main \
  | uv run --project docbot docbot gate --doc-map ../mobivisor/doc-map.json
```

`seed-gitlab.sh` should write the three `DOCBOT_*` lines to `.runtime/docbot.env`, so that
setup becomes one `source`. **[PROPOSED]**

`--dry-run` is what makes the laptop path safe against the *real* forge. It runs
discovery, `/diffs` and the gate, prints what `report` would write, and makes no writes.
This replaces the README's `docker exec … sh -c 'git clone …; docbot'` loop.

### In the evaluation harness

The harness replays historical merge requests through `docbot gate`. It gets the same
function as `process-queue`, fed from files rather than from the forge. This is what the
foundation doc means by "the evaluation harness for free", and it only holds while `gate`
stays pure.

---

## Command surface

| Command | Reads | Writes | Network | Lands in |
|---|---|---|---|---|
| `process-queue [--dry-run] [--max N] [--only IID]` | Forge: queue query, `/diffs`, doc map at the merge commit | Via `report`; then labels | Yes | Queue step 4 |
| `resolve [SHA]` | Forge | Nothing | Yes | Queue step 2, ported from the stub |
| `gate --doc-map PATH [--changed-files PATH\|-]` | Two files | Nothing | **No** | Queue step 3 |
| `report --verdict PATH` | Verdict, forge | Note, verdict label, ledger merge request | Yes | Queue step 6 |
| `screenshots`, `render-reference`, `draft`, `validate` | A checkout, via `--repo PATH` | Varies | Varies | Later; foundation doc |

`--only IID` narrows the queue to one merge request. It does **not** bypass the labels: a
processed merge request stays processed. Re-queueing is still a human removing the label,
as in the queue design.

`process-queue` calls `gate` and `report` **in-process**, as functions. The subcommands
expose the same functions, which is what makes each one testable on its own.

| Rejected | Why |
|---|---|
| `process-queue` shelling out to `docbot gate` | It turns typed errors into exit codes and text parsing on the hot path, and buys nothing the in-process call lacks |

### The gate's input format

`--changed-files` takes `git diff --name-status` output (`M⇥path`, `R100⇥old⇥new`), so the
laptop pipe above is plain git. The GitLab adapter converts `/diffs` into the same
internal shape.

| Option | Verdict |
|---|---|
| One path per line | **Rejected.** It drops a renamed file's old path. Moving code *out of* `public/app/policies/kiosk/` changes the kiosk page's truth as much as editing it does, so the gate must match both paths. The current stub's `new_path`-only projection has this bug |
| JSON | **Rejected.** It cannot be piped from git, and it adds a format nobody else produces |
| `git diff --name-status` | **Chosen. [PROPOSED]** |

---

## Configuration

Precedence is flag, then environment, then default. **DocBot has no config file of its
own.**

| Setting | Home | Why there |
|---|---|---|
| Forge URL, project, token | `DOCBOT_GITLAB_URL`, `DOCBOT_PROJECT`, `DOCBOT_GITLAB_TOKEN` | Deployment config, and the token is a secret. Both executors inject secrets as environment variables |
| Epoch | `DOCBOT_EPOCH` | Deployment config: a second deployment (a staging bot) would differ. It must **not** be editable by a MobiVisor merge request, since moving it re-queues history |
| Run cap | `--max`, default 25 | Per invocation |
| Areas, `docRoot`, languages | `doc-map.json` in MobiVisor, **read at the merge commit** | Facts about the repository. They change with the code they describe |
| Label names | Constants in code | Not configurable. The queue query depends on them, and configurable names would let two deployments disagree about what the queue is |
| Model provider and key | Later: `DOCBOT_LLM_PROVIDER` plus the provider's own variable (`MISTRAL_API_KEY`, as `.env.example` already has) | Out of scope until Q10 |

| Rejected | Why |
|---|---|
| `docbot.toml` in the MobiVisor repo | Puts deployment config, including the epoch, in the reviewed repository |
| A config file baked into the image | Changing the epoch would need an image rebuild |
| The stub's un-prefixed `GITLAB_URL` and `GITLAB_TOKEN` | `glab` and other tools read `GITLAB_TOKEN` **[DOCS]**, so in a shared CI environment it is ambiguous which token is meant. A prefix removes the ambiguity and makes every setting DocBot reads findable with one grep |

Missing required settings fail at startup with exit code 2, naming the variable, before
any network call. The stub's `: "${GITLAB_URL:?}"` guard exists for the same reason.

### Which doc map: the one at the merge commit

| Option | Verdict |
|---|---|
| **At the merge commit** (`?ref=<merge_commit_sha>`, verified above) | **Chosen. [PROPOSED]** Reproducible: judging a merge request twice gives the same verdict. A merge request that changes code *and* its doc-map entry is judged by its own map |
| At `HEAD`, or at the workspace checkout | **Rejected.** Draining a backlog means judging old merges, and the verdict would depend on *when* the drain ran. This is the same failure standing principle 7 exists to prevent, one level down |
| Bundled in DocBot | **Rejected.** The map changes with the console. It would need a DocBot release for every console refactor |

A cost of this choice: fixing a wrong doc-map entry does not re-judge merges already
judged with it. If that is ever needed, it should be a deliberate override
(`--doc-map-ref main`) used on purpose, not a default. **[PROPOSED]**, not for day one.

---

## Output contract

- **stdout: exactly one JSON document**, the command's result (`docbot.verdict/1`,
  `docbot.processed/1`, `docbot.resolution/1`). Nothing else ever writes to stdout, and
  `test_cli.py` asserts it.
- **stderr: the narration**, including the banner the stub prints today. It still shows in
  the Jenkins console log.
- **The result is written even on failure.** A drain that stops on a 401 still emits
  `processed.json`, listing what it finished and the error it stopped on, and then exits
  non-zero. The artifact of a red build shows how far the drain got.

The foundation doc's sketch used `--out processed.json`. This design drops the flag in
favour of a redirect: one way to do it, and it works identically in every executor and
in a shell.

### Exit codes

| Code | Meaning | Jenkins | GitLab CI |
|---|---|---|---|
| 0 | Ran, and every item was handled. **A verdict of `no-doc-impact` or `undecidable` is a result, not an error** | Success | Passed |
| 1 | Infrastructure failure: 401, 5xx, or network error. The drain stopped (queue design, "Failure isolation") | Failure | Failed |
| 2 | Usage or configuration error, raised before any network call. This matches click's own usage-error code **[DOCS]** | Failure | Failed |
| 3 | The drain completed, but at least one merge request was labelled `docbot-failed` | **Unstable** | **Warning** |

| Rejected | Why |
|---|---|
| Exit 0 when items failed | A green build with failed items is the invisible failure this whole design fights. The `docbot-failed` label is visible only to someone who already knows to look |
| Exit 1 when items failed | Makes one bad merge request indistinguishable from GitLab being down, which is the collapse the stub's 200/404/other split exists to prevent |
| `gate` exit code encoding the verdict, like `git diff --exit-code` | Mixes up "the answer is yes" with "something broke". A caller under `set -e` would abort on a verdict |

---

## What changes in `devinfra`

| Change | Why |
|---|---|
| ~~Re-seed the stack from `demo-repo/` (queue design, step 1)~~ **Done 2026-09-23.** The seeded file list and `doc-map.json` are identical to `demo-repo/`; `main` #1 resolved to "not a merge — nothing to do" | Finding 5: the stack still carried the pre-Phase-0 layout |
| ~~`open-test-mr.sh` fails on a missing file instead of creating it~~ **Done** in aa54cc3 | Finding 5: creating missing files is what hid the stale seed |
| ~~Jenkins `Dockerfile`: `python3`, a venv, `COPY --from=docbot`; compose adds `additional_contexts`~~ **Superseded 2026-09-24.** `python3` and `python3-venv` stay. Nothing of DocBot is baked in: the Jenkinsfile installs `tools/docbot/` from the checkout ([docbot-code-location.md](docbot-code-location.md)) | Finding 1, and Packaging |
| ~~Jenkinsfile stage as shown under Invocation; `gitlab-http` becomes a `docbot-gitlab-token` string credential~~ **Done 2026-09-24**, running `update-manual` (HEAD only) until `process-queue` exists | The `DOCBOT_*` names |
| `seed-gitlab.sh` writes `.runtime/docbot.env` | The laptop loop |
| ~~`jenkins/docbot` deleted once `resolve` is ported~~ **Done 2026-09-24.** The resolution is in `tools/docbot/src/docbot/resolve.py` | As the queue design says |

---

## New open questions

Numbering continues from the executor doc.

| # | Question | Blocks |
|---|---|---|
| 19 | `docbot` or `mobimanual` as the executable name? This design assumes `docbot` | Nothing technical; cheap now, churn later |
| 20 | The queue design's "Python, decision requested" is still open. This document builds on Python; does the decision stand? | Step 2 of the queue design |
| 21 | Will the production image be built and hosted by this repository's GitLab project (executor option B), or by a registry the MobiVisor team runs? | Production packaging only; the prototype is unaffected |
