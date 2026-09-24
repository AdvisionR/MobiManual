# DocBot — where the code lives, judged by how it gets into MobiVisor

**Status:** decided and implemented in the fixture on 2026-09-24. The location, with
`typer` and `httpx2`, is at `devinfra/demo-repo/tools/docbot/`. Written the same day
against the running `devinfra` stack.
**Relationship to other documents:** reopens "Where the code lives" and "Packaging" in
[the CLI design](docbot-cli-design.md). That document chose `docbot/` in this repository and
never weighed how the code reaches the real repository. This document also qualifies the
[foundation doc](mobimanual-docbot-foundation.md)'s "Bake the bot into the image rather than
into the watched repository", under "Keep Jenkins thin". The executor question in
[the executor doc](docbot-ci-executor.md) stays open, and this document gives an answer for
either outcome.

Tags as in the foundation doc: **[DECIDED]**, **[EVIDENCE]**, **[PROPOSED]**,
**[UNKNOWN]**, plus **[DOCS]** as defined in the executor doc: taken from upstream
documentation, not reproduced here.

---

## The question

> You plan to put docbot in a separate /docbot directory. How easy is it to adapt this
> structure to a bigger project? Would alternative location for docbot be easier to work
> with or more beneficial in some aspect? […] this is just a demo-repo, and we need to
> integrate docbot into a real repository, so it's important this can happen easily and
> without too many points of potential failure.

## Short answer

- **While Jenkins is the executor, put DocBot in the MobiVisor repository at
  `tools/docbot/`, and run it straight from the checkout.** Integration then takes one
  merge request to MobiVisor and one Jenkins credential. No image is built, pushed or
  pulled. The Jenkinsfile stage installs the dependencies into a venv in the workspace.
  **[DECIDED 2026-09-24]**
- **The CLI design's choice is wrong for the Jenkins shape.** That choice was a separate
  `docbot/`, shipped as an image. It adds a registry, a Docker-capable agent and a
  cross-repository version pin. It pays for an isolation that does not exist: the
  Jenkinsfile that decides what runs is itself in MobiVisor, and a merge request can
  edit it.
- **If the executor moves to GitLab CI, move the code out with it** (option B in the
  executor doc). Only then does separation buy real isolation and independent releases.
  The move stays cheap as long as the package obeys four rules, listed below.
- **Dependencies: `typer` for the CLI and `httpx2` for HTTP. [DECIDED 2026-09-24]**
  They are installed from a hash-locked `requirements.txt` into a venv by the Jenkinsfile
  stage. The model SDKs that the drafting step needs will bring an install step
  whatever is decided today, so it is wired now, while there is only a placeholder to
  debug it with. This document recommended `argparse` over `typer`. Both sides are under
  [Dependencies](#dependencies-judged-against-where-docbot-is-going).
- **A bigger repository changes nothing.** DocBot reads MobiVisor through the GitLab API,
  so its cost grows with the number of merged merge requests, not with the size of the
  tree.

---

## What integration costs, option by option

The test: what has to hold, and who has to act, for a merge to MobiVisor's `main` to
produce a docs merge request. Every option needs a GitLab token in Jenkins, so the token
is left out.

| Option | One-time integration | Must hold on every run | A DocBot release is |
|---|---|---|---|
| **A. `tools/docbot/` in MobiVisor, run from the checkout** | One MobiVisor merge request adding the package, a Jenkinsfile stage and one doc-map line | `python3` 3.10 or newer on the agent that builds `main`, and PyPI (or a mirror) reachable for the install step | A MobiVisor merge request |
| **B. Separate project, pinned image** (the CLI design's production plan) | A docbot project with an image pipeline, a registry the agents can reach, Docker on the agents, the Docker Pipeline plugin, a pull credential, and a MobiVisor merge request for the stage | Registry reachable, pull credential valid, tag pushed, Docker daemon up | Build and push an image, then a MobiVisor merge request that bumps the tag |
| **C. Separate project, `pip install git+…@tag` at build time** | A docbot project, read access to it for Jenkins' credential, and a MobiVisor merge request | `python3` and `venv` on the agent, the docbot project reachable and readable, PyPI reachable for dependencies, the tag exists | A tag, then a MobiVisor merge request that bumps it |
| **D. Git submodule** | Submodule checkout configured in the Jenkins job, with its own credentials | The submodule fetch succeeds | A submodule bump, which is a MobiVisor merge request |
| **E. Separate project with its own GitLab CI pipeline** (executor doc, option B) | A docbot project, a runner, and one webhook on MobiVisor | The runner is up, and the webhook is delivered or the hourly schedule runs | A docbot commit. MobiVisor is not involved |
| *Today's `devinfra`: baked into the Jenkins controller image* | *Rebuilding the controller* | — | *No production counterpart. Nobody will rebuild MobiVisor's Jenkins controller for DocBot, so this shape rehearses nothing about integration* |

Look at the last column. Under Jenkins, options A to D all make a DocBot release a
MobiVisor merge request, because the Jenkinsfile is where the code or its version gets
chosen. Separating the code only changes whether that merge request carries the code or a
pin. Only E takes MobiVisor out of the release path. E is the executor change that the
executor doc proposes, and its question 16 blocks it.

A pin is still a smaller review than a code diff. That is B's and C's real advantage over
A, and the next section weighs it.

## The argument that decides it: under Jenkins, isolation is not available

The foundation doc's reason for keeping the bot out of the watched repository is that "a
bot that reviews a repository should not be editable by the merge requests it reviews".
The CLI design rejected option A on the same ground.

Under Jenkins, no option gives that protection. The Jenkinsfile lives in MobiVisor, and
Jenkins builds a same-project merge request with that merge request's own Jenkinsfile
**[DOCS]**. So an unmerged merge request can already change which image, tag or command
runs, and which credentials are bound while it runs. A pinned image is exactly as editable
as a directory: it is one line away. The CLI design names this "a known limit of the
Jenkins shape" but draws no conclusion from it.

The run that matters most does not need the protection anyway. Drafting runs on `main`
after the merge, with code a human has already reviewed. Advisory mode, which comments on
open merge requests (delivery model A), is the only place a merge request could steer its
own verdict. Under Jenkins, B, C and D are equally exposed to that.

**Not reproduced here.** A probe merge request that added an `echo` stage to its own
Jenkinsfile was blocked by the authoring session's permission guard. To check by hand:
branch from `main`, add a `when { changeRequest() }` stage that echoes something, open the
merge request, and read the console of `MR-<iid>`.

---

## What A costs, stated plainly

| Cost | Size | Mitigation |
|---|---|---|
| Every DocBot change goes through MobiVisor's review process: its approvals, its pipeline rules | The largest cost, during a pilot that iterates on rules and prompts | Iterate against the `devinfra` fixture and from a laptop, and ship tested versions to MobiVisor. B and C also need a MobiVisor merge request for every release, as a one-line pin, so the difference is review size, not review count |
| Python in a JavaScript repository | Organisational. The MobiVisor team would own a directory in a language their CI does not lint | Needs their agreement (question 23). One directory, one hash-locked `requirements.txt`, and nothing installed outside the job's workspace |
| DocBot's own merges land on `main` and trigger DocBot | The monorepo loop again, from a new source | One doc-map line: `^tools/docbot/` as `no-doc-impact` |
| The evaluation harness and these design documents live apart from the code | Small | The harness imports the package from a MobiVisor checkout through `PYTHONPATH` |
| No pinned toolchain image for the later validation gates (Node, Grunt, Pandoc) | Deferred, and possibly a gain | The agents that build MobiVisor are the ones whose toolchain produces the published manual. Validating with that toolchain avoids drift between DocBot's image and the real build. **[UNKNOWN]** whether those agents run `grunt web_docs` today |

## Keeping a later move to E cheap

Four rules, each checkable in review. **[PROPOSED]**

1. **Nothing outside `tools/docbot/` is imported or executed.** DocBot reads MobiVisor
   through the GitLab API, or through an explicit `--repo PATH` for the later commands
   that need files.
2. **Configuration comes only from `DOCBOT_*` variables and flags.** Never from Jenkins'
   own variables (`BRANCH_NAME`, `GIT_COMMIT`, `CHANGE_ID`).
3. **The only thing read implicitly from the working directory is `git rev-parse HEAD`**,
   as the stub does today, and a flag can replace it.
4. **One JSON document on stdout, narration on stderr**, and the exit codes as in the CLI
   design.

With those rules, moving to E means copying the directory next to a Dockerfile and
deleting one Jenkinsfile stage.

## Dependencies, judged against where DocBot is going

The first draft of this document said "standard library only". That was judged against
today's placeholder, and it does not hold up against the roadmap.

### What the later commands need

| Command | Needs | Is the standard library enough? |
|---|---|---|
| `update-manual` today; `process-queue` and `report` next | JSON over HTTPS to GitLab: pagination through `X-Next-Page`, timeouts, and the 401 / 404 / 5xx / network split that sets the exit code. Also tests against a recorded forge (queue design, `test_queue.py`) | Yes, with a wrapper of about 60 lines around `urllib`. The recorded-forge tests then need a hand-built seam. `httpx2.MockTransport` provides one |
| `draft`: the agentic loop (foundation doc, "Agent behaviour rules") | A model API with tool use, retries on rate limits and overload, long or streamed responses, and a thin interface over two providers so they can be A/B tested (foundation doc, "Model provider") | **Not sensibly.** Each provider's SDK already handles retries, streaming and typed tool-use blocks. Redoing that by hand, twice, is exactly the maintenance to avoid |
| `validate` | `grunt`, `pandoc` and Vale, run as subprocesses | Yes |
| `render-reference` | Schema to Markdown tables, possibly through a template engine | Probably. Question 3 decides |
| The CLI itself | About eight subcommands with a few options each, one JSON document on stdout, exit code 2 on misuse | Yes. `argparse` covers all of it |

**The model step brings an install step whatever is decided now.** Every current provider
SDK needs Python 3.10 or newer and pulls in pydantic, anyio and an HTTP client:
**[EVIDENCE]**

| SDK, current release | HTTP client it depends on | Python |
|---|---|---|
| `anthropic` 1.8.0 | `httpx2` | 3.10+ |
| `openai` 3.19.2 | `httpx2` | 3.10+ |
| `mistralai` 2.10.1 | `httpx` 0.28.1 | 3.10+ |

So "standard library only" buys a zero-install run for one milestone. Then it has to be
undone, and it leaves behind a `urllib` wrapper to maintain next to the SDK's HTTP client,
or to rewrite. The install step is also wiring, which is the part this prototype exists
to rehearse. It is better to meet "the agent cannot reach PyPI" now, on a placeholder,
than on the day the model step lands.

### Is the install step a point of failure worth fearing?

Less than the first draft claimed. If PyPI is unreachable, the build fails red before
DocBot writes anything. Once the work queue lands, the next run drains whatever this one
missed, so the cost is a delay, not a lost update. That is the same class of failure as
GitLab being down, which the design already accepts. A hash-locked `requirements.txt`
makes the install reproducible and tamper-evident. The venv lives in the job's workspace,
which Jenkins keeps between builds of `main`, so PyPI is needed only when
`requirements.txt` changes. In the Jenkins image, a second install with `PIP_INDEX_URL`
pointed at a closed port found all 14 requirements already satisfied and exited 0.
**[EVIDENCE]**

### HTTP: `httpx2`, `httpx` or `urllib`

| Option | Verdict |
|---|---|
| `urllib.request` | **Rejected.** It works, but it is the wrapper the SDK makes redundant: two HTTP stacks, one of them hand-written |
| `httpx` | **Rejected, narrowly.** The stable line is still 0.28.1, from late 2024. Development releases of 1.0 have appeared since, the latest being 1.0.dev6 on 2026-08-31, so a major version is pending **[EVIDENCE]**. Of the three SDKs, only `mistralai` still depends on it |
| `httpx2` | **Chosen. [DECIDED 2026-09-24]** Maintained by the pydantic organisation, with the same API: `Client`, `MockTransport` and the error classes were all checked. It is the transport of the `anthropic` and `openai` SDKs, the two providers the foundation doc chose between, so forge and model calls share one HTTP stack. It is young: the first release was in May 2026, and 2.13.1 came out on 2026-09-23 **[EVIDENCE]**. That is why it stays inside one module |
| `python-gitlab` | **Rejected.** It brings `requests` as a second HTTP stack, and it puts an object model between DocBot and the endpoints whose status codes and headers the design relies on |

The GitLab adapter is the only module that imports the HTTP client (CLI design, "Layout"),
so switching between `httpx2` and `httpx` means renaming the import in one file.

### CLI: `argparse` or `typer`

| Option | Verdict |
|---|---|
| `typer` | **Chosen. [DECIDED 2026-09-24]**, against this document's recommendation. Its gains are less boilerplate, shell completion and rich-formatted help. The case against it: DocBot's main caller is CI, and by design `cli.py` holds only argument parsing and exit codes, so typer saves a few dozen lines in one file. It adds `rich`, `shellingham`, `colorama` and `annotated-doc`. Once an install step exists anyway, that weight is small. Checked: typer 0.27.2 does not print local variables in tracebacks by default (`pretty_exceptions_show_locals=False`), so a token held in a local variable is not an argument against it. DocBot also turns rich tracebacks off, so CI logs get plain ones |
| `argparse` | **Recommended here, not chosen.** Subcommands, help, and exit code 2 on misuse: everything the CLI design's contract needs, stable across Python releases, with nothing to install |

| Also rejected | Why |
|---|---|
| Vendored wheels in `tools/docbot/vendor/` | Binary files in MobiVisor's history. Once pydantic arrives with an SDK, the wheels are also platform-specific |
| A venv baked into the agent image | Needs someone to rebuild MobiVisor's agents for each DocBot dependency change. This is the controller-image trick again

## "How easy is it to adapt this structure to a bigger project?"

Two readings, and the location decides neither.

- **A bigger MobiVisor.** DocBot does not walk the tree. Resolution, diffs and file
  contents come from the GitLab API, so repository size and history length cost it
  nothing. The later commands that need a checkout (`draft`, `validate`) get the one
  Jenkins has already made.
- **A bigger DocBot.** It grows by modules inside one package: the gate, the queue, the
  report and the forge adapter, as the CLI design lays out. That growth is the same in
  `tools/docbot/` as it would be in `docbot/`.

---

## What this changes in the prototype

| Before (CLI design) | After |
|---|---|
| `docbot/` at the root of this repository | `devinfra/demo-repo/tools/docbot/`, pushed to GitLab with the rest of the fixture. The fixture stands in for MobiVisor, so seeding it rehearses the real integration |
| The Jenkins image installs a venv; compose gains `additional_contexts` | Nothing DocBot-specific in the Jenkins image. `python3` and `python3-venv` are already there |
| `docbot …` on `PATH` | The Jenkinsfile stage creates a venv in the workspace, installs `tools/docbot/requirements.txt`, and runs `python -m docbot …` |
| `typer`, `httpx` | `typer` and `httpx2` |
| — | A doc-map entry: `^tools/docbot/` as `no-doc-impact` |

Integrating into the real repository is then: copy `tools/docbot/`, copy the Jenkinsfile
stage, add the doc-map line, and create the credential.

## Checked against the stack

| # | Check | Result |
|---|---|---|
| 1 | Python in the `devinfra` Jenkins container | 3.13.5 **[EVIDENCE]** |
| 2 | An unmerged merge request's own Jenkinsfile runs on its `MR-<iid>` build | Not reproduced; see "Not reproduced here" above. **[DOCS]** |
| 3 | Python on the real MobiVisor Jenkins agents | **[UNKNOWN]**, question 22 |
| 4 | Dependencies and `Requires-Python` of `anthropic`, `openai`, `mistralai`, `typer` and `httpx`, read from the installed packages' metadata | As in the tables under "Dependencies". Every one of them except `httpx` needs Python 3.10+ **[EVIDENCE]** |
| 5 | Release history of `httpx`, `httpx2` and `typer` on PyPI | As quoted under "HTTP" **[EVIDENCE]** |
| 6 | `httpx2` exposes `Client`, `MockTransport`, `HTTPStatusError` and `TransportError` | Yes. It is a separate package from `httpx`, imported as `httpx2` **[EVIDENCE]** |
| 7 | The Jenkinsfile's install and run steps, in the `devinfra` Jenkins image (Debian, Python 3.13.5) | The hash-checked install from PyPI succeeds. `python -m docbot` runs through `PYTHONPATH`. Missing settings exit 2 with an empty stdout. A reinstall needs no index **[EVIDENCE]** |

---

## New open questions

Numbering continues from the CLI design.

| # | Question | Blocks |
|---|---|---|
| 22 | Do the Jenkins agents that build MobiVisor's `main` have `python3` 3.10 or newer, with `venv`? Can they reach PyPI directly, or only through a mirror? | Option A. Without Python, the agent needs it installed, which C needs too; B needs Docker instead. A mirror only changes the install line |
| 23 | Will the MobiVisor team accept a Python directory, `tools/docbot/`, in their repository, and review changes to it? | Option A. A "no" means C under Jenkins, or pressing for E |
