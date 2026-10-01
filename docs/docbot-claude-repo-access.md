# DocBot — letting Claude read the repository

**Status:** design, pre-implementation. Written 2026-09-30 against `tools/docbot/` as it
stands after the placeholder step and [the LLM draft plan](docbot-llm-draft.md). The
Claude facts were read from Anthropic's current documentation the same day, and the
package facts were resolved with `uv pip compile` (see "What was checked"). Decided the
same day:

- Claude is integrated through the **Client SDK** (`anthropic`), with DocBot owning the
  loop and the tools. The Agent SDK, Managed Agents and Claude Code for GitLab CI are not
  used

Still open: whether repo access is adopted at all. That is settled by the comparison on
the corpus, under "How to decide".

**Relationship to other documents:** this is a deliberate deviation from two items the
LLM draft plan **[DECIDED 2026-09-24]**: "the model sees the diff, not the repository"
and "one drafting call with repair, not an agent loop". Both stand as the baseline until
the comparison is run. It moves back toward the
[foundation doc](mobimanual-docbot-foundation.md)'s **[DECIDED]** "agentic loop with file
access" under "Agent behaviour rules", and it answers the open question in
`current-state.md`, roadmap item 2: "What access should AI have?".

Tags as in the foundation doc: **[DECIDED]**, **[EVIDENCE]**, **[PROPOSED]**,
**[UNKNOWN]**, plus **[DOCS]** as defined in the executor doc: taken from upstream
documentation, not reproduced here.

---

## The question

> How could docbot include an AI integration with Claude where Claude has repo read
> access and searches for necessary files itself. This is a deviation from the current
> plan, but I wanted to see if this is possible. Also research how this could be
> deployed to the real MobiVisor.

## Short answer

- **It is possible, and it fits the current design without restructuring.** DocBot
  already runs inside a MobiVisor checkout at the merge commit (Jenkins, option A of the
  code-location doc). Giving Claude three read-only tools (`list_files`, `grep`,
  `read_file`) over that commit, plus a `submit_proposal` tool that takes the existing
  `docbot.proposal/1` shape, turns the drafting step into a loop. Everything around it
  stays: the ignore list, triage, validation, applying the edits, the docs merge
  request and `result.json`. The LLM draft plan predicted this: "the loop will wrap
  this step, not replace it".
- **DocBot owns the loop and the tools, and calls Claude through the Client SDK, the
  plain `anthropic` package. [DECIDED 2026-09-30]** The alternatives are the Claude Agent
  SDK (Claude Code as a library), Managed Agents, and Claude Code's GitLab CI
  integration. All three work, and all three are rejected, for the reasons under
  Decision 1.
- **The tools read git objects, not the file system.** They run `git grep <sha>` and
  `git show <sha>:<path>`, so the model sees exactly the merged commit. Nothing
  untracked (`.venv`, `.env`, build output) is visible, and there is no path to
  traverse. A deny list in `doc-map.json` names paths that may never leave the network.
  Every path read is logged in `result.json`, so each run records exactly which files
  went to the provider.
- **Repo access has to earn its place on the corpus.** The fixture is 31 KB of text, so
  the whole repository fits in one prompt and cannot show what searching adds. The
  proposal is to run both modes on the same scenarios, `--context diff` and
  `--context repo`, add one scenario whose manual impact the diff alone does not reveal,
  and adopt repo access only if it wins. That is the foundation doc's own rule: widen
  to repository access "only if drafting quality demonstrably needs it".
- **Deploying to the real MobiVisor comes down to one question: where may inference
  run?** The code is the same everywhere. Only the client constructor changes.
  - **Anthropic's API** (or Claude Platform on AWS): inference is US or global, data
    at rest is stored in the US, and zero data retention (ZDR) can be arranged with
    Anthropic's sales team.
  - **EU-only processing** exists only through **Amazon Bedrock** (Frankfurt, or an EU
    inference profile) or **Google Vertex AI** (the `eu` multi-region), each at a 10%
    premium, with AWS or Google as the data processor.
  - This belongs to question 10, the data-governance sign-off. It already blocks the
    real repository, and repo access raises its stakes: more than the diff leaves the
    network.
- **A side finding, now corrected in the LLM draft plan:** `mistralai` 3.0 depends on
  `httpx2`, as `anthropic` 1.x does. Either adapter shares DocBot's single HTTP stack,
  and the "two HTTP stacks" cost under Decision 3 of that plan no longer applies
  **[EVIDENCE]**.

---

## What repo access buys, and what it does not

The LLM draft plan gives the model the diff, the table of contents, and the pages that
triage picked. That misses three things, and each one needs the repository:

| Gap | Example in the fixture | What the model does with repo access |
|---|---|---|
| **Following a change to the page it affects.** The diff shows *what* changed, not *where the user sees it* | A change in `server/protocol/…`, or in a controller helper. The page follows from `public/app/routes.js` and the route-to-filename rule, and neither is in the diff | `grep` for the changed function's callers, then read `routes.js`: `#!/policies/kiosk` → `_policies_kiosk.md` |
| **Using the manual's own terms.** "Kiosk mode", "Enrollment > iOS", bold UI labels | Pages triage did not pick still define the vocabulary | `grep` the English manual for the term before writing it |
| **Checking a claim against the code**, not the diff alone | Whether a new field is required or optional is set by a line outside the hunk | `read_file` on the template or controller around the hunk |

What it does **not** buy:

- **A build to iterate against.** That is the other half of the foundation's loop, and
  it still waits for `validate` (the LLM draft plan, Decision 2).
- **Better gating.** Triage stays one cheap call without tools. Most merges should end
  at the ignore list or at triage, before any file is read (standing principle 3).

## Decision 1 — which way to give Claude the repository

| Option | Verdict |
|---|---|
| **Keep the diff only** (the LLM draft plan) | **Kept as the baseline, not replaced.** It is the control arm of the comparison under "How to decide" |
| **A. DocBot's own loop, own read-only tools, the Client SDK (`anthropic`)** | **Chosen. [DECIDED 2026-09-30]** See below. This is the "Client SDK, you write the tool loop yourself" row of the Agent SDK overview's comparison table **[DOCS]** |
| B. The same Client SDK, with its Tool Runner (`client.beta.messages.tool_runner`) driving the loop | **Not chosen.** It saves about 30 lines of loop. But it is beta, it is Anthropic-only, which breaks the provider seam, and every turn still has to be logged per standing principle 4, which a hand-written loop does naturally. It uses the same package as A, so switching later costs only the loop |
| C. **Claude Agent SDK** (`claude-agent-sdk`, Claude Code as a library) with `tools=["Read", "Glob", "Grep"]`, `permission_mode="dontAsk"`, `cwd=<checkout>` and `output_format` for the proposal **[DOCS]** | **Rejected. [DECIDED 2026-09-30]** Least code, and a well-tested harness. But the agent is the proprietary Claude Code binary: the MIT-licensed Python package bundles it and runs it as a subprocess that talks JSON over stdin and stdout **[EVIDENCE]**, and the binary's use is governed by Anthropic's Commercial Terms. The harness cannot be inspected, and it changes with every SDK release, which blurs the corpus comparison. It is Claude-only, so no A/B against Mistral or OpenAI on the same harness. The binary is 224 MB unpacked, and wheels exist only for macOS and glibc Linux **[EVIDENCE]**. It sends traffic besides model calls: metrics logging is exempt from ZDR **[DOCS]**. It can also load `.claude/` settings and `CLAUDE.md` from the repository it reads, which then steer the bot unless `setting_sources` is locked down. **Revisit** only if the own loop clearly misses the scenarios' expectations in a way that points at the harness rather than the model or the tools. Then the middle ground is the Agent SDK with its built-in tools switched off and DocBot's `repo.py` functions registered as custom tools |
| D. **Managed Agents** (Anthropic hosts the loop, sandbox cloud or self-hosted) | **Rejected. [DECIDED 2026-09-30]** Cloud sandboxes mount GitHub repositories only **[DOCS]**, so MobiVisor on GitLab would have to be cloned into Anthropic's sandbox, meaning the whole repository leaves the network. Self-hosted sandboxes keep the files local, but need an always-on worker. Managed Agents is in beta, is not ZDR-eligible (transcripts persist until deleted, self-hosted included), and is not offered on Bedrock or Vertex, so it has no EU route **[DOCS]** |
| E. **Claude Code for GitLab CI/CD** (maintained by GitLab, beta) | **Rejected. [DECIDED 2026-09-30]** It is built for `@claude` mentions that implement changes: `Bash Edit Write` plus a GitLab token, with the agent opening merge requests itself **[DOCS]**. That bypasses DocBot's contract: idempotent `docbot/mr-<iid>`, the label, validation and `result.json`. It needs a `.gitlab-ci.yml` in MobiVisor, which the executor doc rejected as option A. It is useful as evidence: the Claude Code CLI runs in GitLab runners against Bedrock and Vertex through OIDC |

**Why A.** DocBot's task is small for an agent: roughly 5 to 25 searches and reads, then
one structured answer. At that size a tuned harness buys little, and A is the smallest
change that keeps every standing decision:

- **The provider seam survives.** The seam grows from one call to one turn with tool
  calls. Tool calling is common to Claude, Mistral and OpenAI, so the Mistral adapter
  can implement the same turn, and an A/B on the corpus stays possible.
- **The tool boundary is DocBot's code.** Three pure functions over `git`, unit-tested
  like `edits.py`, with typed arguments DocBot can cap, deny and log. The agent-design
  guidance says to promote an action to a dedicated tool exactly when you need to gate
  or audit it. A generic `bash` or `Read` gives the harness only an opaque string.
- **One dependency, one HTTP stack.** `anthropic` 1.9.0 brings 8 packages on top of
  DocBot's current 14 and resolves to the same `httpx2==2.13.1` that `gitlab.py` uses.
  The Agent SDK brings 23 **[EVIDENCE]**.
- **Every cloud route is a constructor.** `Anthropic()`, `AnthropicBedrockMantle(...)`
  and `AnthropicVertex(...)` share the Messages surface **[DOCS]**. DocBot validates
  answers itself, so it does not matter that Bedrock's Messages endpoint lacks
  structured outputs **[DOCS]**.

## The design

```
update-manual                      unchanged: resolve, skip docbot-generated, docbot/mr-<iid>
  ├── ignore.py      pure    as in the LLM draft plan
  ├── triage.py      model   as in the LLM draft plan: one call, no tools
  ├── repo.py        pure    git-backed tools over one commit: list_files, grep, read_file, with caps and the deny list
  ├── agent.py       model   the loop: turn → run tool calls → append results → until submit_proposal or a limit
  ├── edits.py       pure    as in the LLM draft plan
  └── publish        API     as in the LLM draft plan
```

### Tools

| Tool | Implementation | Cap **[PROPOSED]** |
|---|---|---|
| `list_files(glob)` | `git ls-tree -r --name-only <sha>`, filtered | 300 paths |
| `grep(pattern, glob?)` | `git grep -n -I -E <pattern> <sha> -- <glob>` | 100 matching lines, each cut to 300 characters |
| `read_file(path, start?, end?)` | `git show <sha>:<path>`, sliced | 400 lines per call |
| `submit_proposal(pages, uncertainties)` | Validated as `docbot.proposal/1` by the existing rules | — |

- **Reading the commit, not the working tree** makes a run reproducible from the sha
  alone. It also means the tools do not care whether the checkout is Jenkins'
  workspace or a clone in a GitLab CI job.
- **The deny list** is a new `private` section in `doc-map.json`, regexes in the same
  form as `ignore`. A denied path does not appear in `list_files` or `grep` output, and
  `read_file` refuses it with a tool error. It is read at the merge commit, like the
  rest of the doc map. That is acceptable because drafting runs after human review, the
  same argument the code-location doc makes for the Jenkinsfile.
- **No write tool, no shell, no network.** The worst a planted instruction in the code
  can do is steer a draft that a human then reviews, or make the model read files the
  deny list allows anyway.

### The loop

- **Input:** the same as the LLM draft plan's draft call (the merge request, the diff,
  the table of contents and the picked pages), plus the tools and one instruction:
  search before assuming, and stop as soon as the pages can be made true.
- **End:** the model calls `submit_proposal`. The current models reject forcing a tool
  choice (`tool_choice` `any` or `tool` returns a 400 on Opus 5.5 and Sonnet 5.5
  **[DOCS]**). So a turn that ends in text instead gets one follow-up that names the
  tool. That is the same pattern as the LLM draft plan's repair.
- **Validation failures return as tool errors** (`is_error: true`) with the exact
  problem, such as a `find` that does not match or an unknown page. The model gets
  another try inside the same loop. This replaces the separate repair call.
- **Limits:** at most 25 tool calls and a token budget per run **[PROPOSED]**. At
  either limit the outcome is `needs-human`, "search did not converge", with the
  transcript in `result.json`.
### How the loop holds its state

The API keeps no state between calls, so **DocBot sends the whole conversation on every
turn**. Claude never runs anything and never holds the files. It answers each request with
text or a tool call, and DocBot keeps control between every pair of turns: it decides
whether to run, refuse or cap each call, and when to stop.

```
request 1:  system + tools + [user: task]
response 1: [assistant: tool_use grep(...)]
request 2:  system + tools + [user: task]
                           + [assistant: tool_use grep(...)]      Claude's own turn, sent back unchanged
                           + [user: tool_result ...]              what repo.py returned
response 2: [assistant: tool_use read_file(...)]
...
response n: [assistant: tool_use submit_proposal(...)]            validated, then the loop ends
```

Consequences for the code:

- **Append only.** Each response's `content` goes back exactly as received, thinking
  blocks included, and earlier messages are never edited, reordered or trimmed. Current
  models bind their thinking to the exact history that produced it, and an edited history
  loses it, or is rejected with a 400 on newer accounts **[DOCS]**. An edit also
  invalidates the prompt cache from that point on.
- **Prompt caching.** The unchanged prefix of each request is served from a cache kept
  for 5 minutes, at a tenth of the input price, so each turn pays full price only for
  what is new. One top-level `cache_control` setting enables it, and
  `usage.cache_read_input_tokens` shows whether it works.
- **The transcript lives only in DocBot.** That is what makes `result.json` a complete
  record of what the model saw, and why nothing needs to persist on Anthropic's side,
  which suits ZDR.

### Logging

`result.json`'s `draft` section becomes a list of turns. Each turn holds the tool calls
with their arguments, the size of each result, the model's usage and the `stop_reason`.
The file content itself is left out, because it can be rebuilt from the sha. A
`files_sent` summary lists every path whose content reached the provider. That list is
the answer to question 10's "what left the network", per run.

### Cost

**A context grows with what Claude reads, not with the size of the repository.** Every
tool result is capped, so the repository's size cannot push it over. What a large
repository does change is the **number of turns**: a search for a common name hits the
cap, and Claude has to narrow it. Whether a typical MobiVisor run takes 5 turns or 25 is
**[UNKNOWN]** until DocBot runs against the real repository, which questions 10 and 11
still block. The fixture's scenarios measure cost per run, but not this.

What is known:

- **The real manual is small.** `combined.html` holds 18,515 words of English text in 15
  chapters. The median chapter has 899 words and the largest has 2,980 **[EVIDENCE]**.
  That is roughly 25k to 35k tokens for the whole English manual, estimated from the
  word count rather than counted with the API. So the three pages triage may pick come
  to at most about 12k to 15k tokens.
- **The caps bound each turn.** A full `grep` is 100 lines × 300 characters, about 10k
  tokens. A full `read_file` is 400 lines, about 5k to 6k tokens.

An estimate on Claude Opus 5.5 ($4 input, $5 cache write, $0.20 cache read and $20 output
per million tokens **[DOCS]**), with tokens estimated from characters:

| | Typical guess **[PROPOSED]** | Worst case under the caps |
|---|---|---|
| Starting task: system prompt, tools, diff, table of contents, pages | ~25k tokens | ~35k (a large diff, three long pages) |
| Tool calls × result size | 15 × ~2k | 25 × ~10k (every call hits its cap) |
| Largest single request | ~55k tokens | ~285k (well below the 1M context window) |
| New input, written to the cache | ~55k, $0.28 | ~285k, $1.43 |
| History re-read from the cache | ~585k, $0.12 | ~3.9M, $0.78 |
| Output, including thinking | ~16k, $0.32 | ~50k, $1.00 |
| **Per drafted merge request** | **about $0.70** | **about $3.20** |

The output row is the least certain, because thinking depends on the effort setting.
Merges that stop at the ignore list or at triage cost nothing, or one small call. The
model choice stays question 24. Opus 5.5 and Sonnet 5.5 should both be measured on the
corpus.

A side note on the LLM draft plan's Decision 1: at 25k to 35k tokens, the whole English
manual fits in one cached prompt for a few cents. That weakens the cost argument it gives
against sending the whole manual, but not its argument about scaling.

## Deploying to the real MobiVisor

Two independent choices: **where DocBot runs** (already covered by earlier docs) and
**where inference runs** (new here).

### Where DocBot runs: no new decision

| Executor | Where the repository comes from | Change |
|---|---|---|
| **Jenkins, option A** (current, **[DECIDED 2026-09-24]**) | The workspace is already a MobiVisor checkout at the merge commit, the one `resolve` reads with `git rev-parse HEAD` **[EVIDENCE]** | None. `--repo .` is the default |
| **GitLab CI, option B of the executor doc** | The `docbot` project's job has no MobiVisor checkout | `git fetch --depth 1 <mobivisor> <sha>` with the project access token DocBot already needs. The code-location doc's rule 1 already reserved `--repo PATH` for this |

The credential is one more `withCredentials` binding in Jenkins, or one more masked
variable in GitLab CI, next to the GitLab token. The cloud routes can also use short-lived
credentials through OIDC instead of a stored key (see "Claude Code for GitLab CI/CD"
**[DOCS]**).

### Where inference runs: the governance question

| Route | Inference location | Data processor, retention | EU-only processing | Notes |
|---|---|---|---|---|
| **Claude API** (`api.anthropic.com`) | `inference_geo`: `global` (default) or `us` (+10%). Workspace data at rest: `us` only **[DOCS]** | Anthropic. Conversation content is not retained by default. ZDR by contract with sales; Claude Opus 5.5 and Sonnet 5.5 are eligible, Fable 5.x is not **[DOCS]** | **No** | Full feature set, same-day models |
| **Claude Platform on AWS** | As the Claude API **[DOCS]** | Anthropic, same policy. AWS billing and IAM | **No** | For an AWS-billed organisation |
| **Amazon Bedrock** (`AnthropicBedrockMantle`) | Global, or regional: `eu-central-1` Frankfurt, or an EU inference profile. Regional costs +10% **[DOCS]** | AWS. "Zero operator access": Anthropic staff cannot reach the inference infrastructure **[DOCS]** | **Yes** | No Batches or Managed Agents, and no structured outputs on this endpoint. DocBot needs none of them |
| **Google Vertex AI** (`AnthropicVertex`) | `global`, or the `eu` multi-region (+10%). Single-region endpoints serve Sonnet 4.6 and older only **[DOCS]** | Google | **Yes** | Structured outputs supported |
| **Microsoft Foundry** | **[UNKNOWN]** for an EU option. The docs name a US Data Zone only | Anthropic (per the retention doc) | **[UNKNOWN]** | Not investigated further |

What this means for question 10:

- **Diff only vs. repo access is a governance difference, not only a design one.** With
  the diff, the provider sees what changed. With repo access, it also sees whatever
  the model chose to read, bounded by the deny list and recorded in `files_sent`. The
  sign-off should name which of the two it covers.
- **If the sign-off requires EU processing, the route is Bedrock or Vertex**, and the
  company needs an AWS or GCP account with Claude enabled. For DocBot that is a
  different adapter constructor and credential, not a different design.
- **If Anthropic's API is acceptable, ask for ZDR in writing** before the real
  repository is used, as the foundation doc's "Model provider" section already
  requires. Then keep to ZDR-eligible features. The Messages API with client-side
  tools is eligible. Code execution, the Files API and Managed Agents are not **[DOCS]**.

---

## How to decide: run both modes on the corpus

The scenarios under `devinfra/scenarios/` already carry expected outcomes. The proposal:

1. **Add a fifth scenario** whose manual impact is visible only through the repository
   **[PROPOSED]**. Example: a backend change to the kiosk policy payload with no change
   under `public/app/`. The expected answer is `_policies_kiosk.md`, reached through the
   controller that calls it and `routes.js`. With the diff only, the model has to guess
   the page from the table of contents alone.
   **[CORRECTED 2026-10-01]** This example cannot separate the modes: triage picks the
   pages and has no tools in either mode, and drafting may only edit the pages triage
   picked. The fifth scenario that was built, `account-expiry`, targets the third gap
   under "What repo access buys" instead: a fact the edit needs that is outside the
   diff. See the Mistral prototype doc, "Progress", and its question 35.
2. **Run every scenario with `--context diff` and `--context repo`**, with the same
   model and the same triage, and record each outcome against its expectation, plus
   cost and the `files_sent` list.
3. **Adopt repo access if it gets more scenarios right** without breaking the
   `refactor` scenario's silence. If it does not, the diff-only design stands and this
   document is the record of why.

The fixture is small enough that `--context diff` could be widened to "the whole
repository in the prompt". Do not do that. It would win on the fixture and fall apart
on the real repository, which is the thing being measured.

## Sequenced steps

| # | Step | Depends on | Rough size |
|---|---|---|---|
| 1 | The LLM draft plan's steps 1, 2 and 4: `ignore.py`, `manual.py`, `edits.py`, validation, the LLM seam | — | As planned there. Needed by both modes |
| 2 | `repo.py` with the deny list and caps, and its tests against a small temporary git repository | — | Half a day. No model, no stack |
| 3 | The `anthropic` adapter's turn with tool calls, `agent.py`, `--context diff\|repo`, turn logging, with fake-client tests that replay scripted turns | 1, 2 | A day |
| 4 | The fifth scenario, then both modes across the corpus, recorded against expectations, with cost per run | 3, question 30 | Half a day. Pushes run from your terminal |
| 5 | Decide repo access from step 4. If adopted, update the LLM draft plan's decisions and the foundation's "Model provider" | 4 | — |

The Agent SDK spike that an earlier draft of this document suggested is dropped with
the decision for the Client SDK.

---

## What was checked

| # | Check | Result |
|---|---|---|
| 1 | Size of the fixture's text files (`.js`, `.md`, `.json`, `.html`) | 30,970 bytes in 95 files **[EVIDENCE]** |
| 2 | `anthropic` on PyPI | 1.9.0, Python ≥ 3.10, depends on `httpx2>=2.0,<3` **[EVIDENCE]** |
| 3 | `claude-agent-sdk` on PyPI | 0.2.162, Python ≥ 3.10. Platform wheels of 93 to 103 MB, for macOS (arm64, x86_64) and manylinux (x86_64, aarch64) only **[EVIDENCE]** |
| 4 | What the macOS arm64 wheel contains | `claude_agent_sdk/_bundled/claude`, a 224 MB Mach-O executable that reports `2.1.285 (Claude Code)`. `subprocess_cli.py` starts it with `anyio.open_process` and `--input-format stream-json --output-format stream-json`. No Node is needed **[EVIDENCE]** |
| 5 | Licences | `claude-agent-sdk-python`: MIT. `claude-code`: "© Anthropic PBC. All rights reserved. Use is subject to Anthropic's Commercial Terms of Service." **[EVIDENCE]** |
| 6 | Resolved package counts with DocBot's `typer` and `httpx2` (`uv pip compile`, Python 3.13) | 14 without a provider. 22 with `anthropic`, 25 with `mistralai`, 37 with `claude-agent-sdk`. All resolve to `httpx2==2.13.1` and none pulls in `httpx` **[EVIDENCE]** |
| 7 | Which `mistralai` resolved | 3.0.0, which depends on `httpx2`. The LLM draft plan's "`mistralai` uses `httpx` 0.28.1" was true of the version checked then, and is now corrected there **[EVIDENCE]** |
| 8 | Inference and storage geography on Anthropic's API | `inference_geo` only `us` or `global`. Workspace geo only `us` **[DOCS]** |
| 9 | ZDR eligibility | Messages API: yes. Managed Agents, including self-hosted sandboxes: no. Code execution: no. Fable 5.x: only with Anthropic's express authorisation **[DOCS]** |
| 10 | EU availability of current models | Bedrock: Opus 5.5, Sonnet 5.5 and Haiku 4.5 on the global endpoint, and in EU regions and the EU profile. Vertex: `eu` multi-region **[DOCS]** |
| 11 | Managed Agents repository mounts | `github_repository` only **[DOCS]** |
| 12 | Size of the real English manual, from `combined.html` with tags stripped | 113,718 characters, 18,515 words, 15 chapters. The median chapter has 899 words, the largest 2,980 **[EVIDENCE]** |

Not checked: `git grep` performance on the real MobiVisor tree, and how many turns a
run takes there. The editor session cannot reach the stack, and the
real repository is not available here (foundation question 11).

## New open questions

Numbering continues from the LLM draft plan.

| # | Question | Blocks |
|---|---|---|
| 28 | Does question 10's sign-off require inference inside the EU? If yes, which cloud account (AWS or GCP) may DocBot use? | The provider route for the real repository |
| 29 | If Anthropic's API is used directly: does the company have, or will it request, a ZDR arrangement? | Using the real repository on that route |
| 30 | May the synthetic fixture go to Anthropic, as question 25 allowed for Mistral? And who provides the key? | Step 4 |
| 31 | Which MobiVisor paths belong on the deny list? Candidates: licensing, customer-specific configuration, anything security-relevant in `server/` | Repo access on the real repository |
| 32 | Does the MobiVisor team want DocBot to read beyond the diff at all, given that the reads are logged per run? | Adopting repo access, whatever step 4 shows |
