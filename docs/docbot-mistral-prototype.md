# DocBot — what a working Mistral prototype needs

**Status:** implementation sketch, pre-implementation. Written 2026-09-30 against
`tools/docbot/` as it stands after the placeholder step. The Mistral facts come from the
`mistralai` 3.0.0 wheel, inspected locally, and from Mistral's documentation, read the
same day (see "What was checked").
**Relationship to other documents:** this puts two plans into one build order. It uses
[the LLM draft plan](docbot-llm-draft.md) (its steps 1, 2 and 4 to 8, and Mistral for the
prototype, **[DECIDED 2026-09-24]**) and [the repo-access doc](docbot-claude-repo-access.md)
(the Client-SDK loop, **[DECIDED 2026-09-30]**, and the `--context diff|repo` comparison).
It makes four small decisions of its own, all **[PROPOSED]**. Claude comes later, as a
second adapter behind the same seam, once question 30 is answered.

Tags as in the foundation doc: **[DECIDED]**, **[EVIDENCE]**, **[PROPOSED]**,
**[UNKNOWN]**, plus **[DOCS]** for upstream documentation not reproduced here.

## Progress

**2026-09-30: the harness and the drafting step are built**, in `tools/docbot/`: the
seam (`llm/__init__.py`), the Mistral adapter (`llm/mistral.py`), the loop
(`llm/agent.py`), the git tools (`drafting/repo.py`), the edits (`drafting/edits.py`)
and the drafting conversation (`drafting/proposal.py`). There are 50 offline tests,
and ruff and pyright are clean. Not built yet: `ignore.py`, `manual.py`, triage, and wiring into
`update-manual`. Steps 3 (in part), 5 (in part) and 7 of the build order remain.

Where the build differs from the sketch below:

- **The drafting step is `proposal.py`, not a reworked `draft.py`.** The placeholder
  stays in place, and `update-manual` keeps working, until the wiring step replaces it.
- **The prompt is a constant in `proposal.py`**, not a file under `prompts/`.
- **The modules sit in two packages**, not flat (2026-10-01). `llm/` holds the seam,
  the adapter and the loop, none of which knows about manuals. `drafting/` holds
  `proposal.py`, `repo.py`, `edits.py` and the placeholder, renamed from `draft.py` to
  `placeholder.py`. `triage.py`, `manual.py` and `ignore.py` belong in `drafting/`
  too. The live tests and their helper are in `tests/live/`.
- **`read_file` is capped at 500 lines**, not 300. The worst case is then about
  35k + 20 × 7k ≈ 175k tokens, still inside 256k.
- **An edit's `find` tolerates whitespace differences.** If the snippet is not in the
  page as it stands, it is matched word by word with any whitespace between the words,
  and it must still match exactly once. The first live run showed why: `_devices.md` is
  hard-wrapped, and the model wrote the wrapped sentence on one line seven times before
  it matched. After the change, the same scenario took one turn.
- **No `DOCBOT_LLM_PROVIDER` yet.** It comes with the second provider.
- **Connection failures arrive as `httpx2.TransportError`**, not as the SDK's own
  errors **[EVIDENCE]**, so the adapter catches both. `gitlab.py` stays the only module
  that sends requests with `httpx2` itself.

**The live run** (`pytest -m live`), `mistral-medium-3-5`, 2026-09-30 **[EVIDENCE]**.
The model was given the pages each scenario's `Expected:` line says triage picks.
Cost is at $1.5 per million input tokens, $0.15 per million cached input tokens and
$7.5 per million output tokens:

| Scenario | Mode | Turns | Result against `Expected:` | Tokens (in / cached / out) | Cost |
|---|---|---|---|---|---|
| `kiosk-passcode` | diff | 1 | Full match: sentence corrected, exit-passcode step added, `_kiosk_mode_1.png` flagged | 952 / 0 / 888 | $0.008 |
| `kiosk-passcode` | repo | 8 | Sentence corrected. No step added, screenshot not flagged | 12,139 / 0 / 554 | $0.022 |
| `ios-department` | diff | 1 | Department step added before Finish. Does not say that Finish needs one | 1,026 / 0 / 598 | $0.006 |
| `ios-department` | repo | 11 | As in diff mode | 18,315 / 2,944 / 550 | $0.028 |
| `devices-filter` | diff | 1 (8 before the whitespace fix) | Filter added to the paragraph, `_devices_id.md` no-change, screenshot flagged | 939 / 0 / 414 | $0.005 |
| `devices-filter` | repo | 10 | As in diff mode. One rejected submission (a page left out), corrected | 15,222 / 7,168 / 674 | $0.021 |

What it shows:

- **The harness works end to end**: tool calls, results, the rejection-and-correction
  path, and the budget.
- **Prompt caching hits across turns** in some repo-mode runs, but not all.
- **On this fixture, repo mode costs 3 to 4 times more and is not better.** In the
  kiosk case it was worse. The model searched for HTML templates the fixture does not
  have. That matches the repo-access doc's warning that the fixture cannot show what
  searching adds. The fifth scenario still has to be built.

---

## The question

> Sketch what is needed for a functioning prototype for the Mistral Adapter.

## What "functioning" means

The prototype is done when all four of these hold:

1. **On a laptop:** `docbot update-manual --sha <merge> --dry-run` prints a real diff of
   real manual pages, drafted by Mistral, for a scenario merge.
2. **Through Jenkins:** a scenario merge opens a docs merge request `docbot/mr-<iid>` that
   edits `public/doc/en/_*.md`, and `docbot-changes.md` is gone.
3. **Silence:** the `refactor` scenario and the comment kinds end as `skipped` or
   `no-doc-impact`, and no merge request opens.
4. **Both modes:** every scenario has been run with `--context diff` and
   `--context repo`, and each outcome is recorded against its `Expected:` line.

**Out of scope:** the Claude adapter (question 30), `validate` (the build as a gate),
page classes (question 27), translations (question 1), the queue, and `report`.

## Short answer: the parts

```
update-manual
  ├── resolve, skip docbot-generated, docbot/mr-<iid>          unchanged
  ├── ignore.py        pure    doc-map ignore list → the files that matter, or skipped
  ├── manual.py        pure    htmlDocPages + headings → table of contents
  ├── triage.py        model   a conversation whose only tool is submit_triage
  ├── repo.py          git     list_files, grep, read_file at the merge commit (only with --context repo)
  ├── agent.py         pure    the loop, for both calls: step → run tools → add results → until submit
  ├── draft.py         model   a conversation with the repo tools (or none) and submit_proposal
  ├── edits.py         pure    proposal + page texts → new page texts, or an error for the model
  ├── llm/__init__.py  pure    the seam: Conversation, Tool, ToolCall, ToolResult, Turn, choosing the adapter
  ├── llm/mistral.py   API     the only module that imports mistralai
  └── publish          API     one commit with every edited page, the description, the new outcomes
```

In numbers: about eight new or reworked modules, one new dependency (`mistralai`, 11
packages), three new settings, one Jenkins credential, and tests that need neither a
key nor the stack, except for one live smoke test.

---

## Decision A — one loop for both calls

Both triage and drafting are **conversations that end when the model calls a submit
tool**. Triage has one tool, `submit_triage`, and drafting has `submit_proposal` plus
the repo tools in `repo` mode. `agent.run()` drives both.

| Option | Verdict |
|---|---|
| Triage through `response_format` `json_schema`, and drafting through the loop | **Rejected.** That means two mechanisms, two validation-and-repair paths, and two things to port to Claude |
| **Both through the loop, each ending at a submit tool** | **Chosen. [PROPOSED]** A validation error goes back as a tool result, and the model tries again in the same conversation. That is the LLM draft plan's "one repair", generalised to "up to the turn limit" |

With Mistral, `tool_choice="any"` on every turn means the conversation can only end
through a tool call **[EVIDENCE]**: `ToolChoiceEnum` has `auto`, `none`, `any` and
`required`. So there is no need for the "please call submit" follow-up that Claude
needs.

## Decision B — where the inputs come from

| Option | Verdict |
|---|---|
| Everything through a local checkout (`--repo`) | **Rejected for now.** Then `--context diff` would need a checkout too, and the tests for `update.py` would need a git repository |
| Everything through the GitLab API, the tools included | **Rejected.** `grep` over the API needs GitLab's search, whose behaviour on CE was never checked. One call per `read_file` is slow |
| **The inputs through the API, as today. The repo tools through local git** | **Chosen. [PROPOSED]** The merge request, the diff, `gruntfile.js` and the pages come through `gitlab.py`, which the existing `Forge` fake already tests. Only `repo` mode needs `--repo PATH`, the checkout that contains the merge commit |

`repo.py` checks `git cat-file -e <sha>^{commit}` before the first call. If the commit
is missing, DocBot exits with code 2 and names the flag. In Jenkins the workspace is the
checkout **[EVIDENCE]**. On a laptop that means a clone of the stack's project,
refreshed with `git fetch`, run from your terminal.

## Decision C — one set of limits, sized for the smallest window

Mistral Medium 3.5 has 256k tokens of context **[DOCS]**, against 1M for Claude. The
worst case under the repo-access doc's caps is about 285k, which does not fit.

| Option | Verdict |
|---|---|
| Limits per model | **Rejected for the prototype.** The same scenario would then run under different limits on each provider, which confounds the A/B |
| **One set that fits 256k** | **Chosen. [PROPOSED]** At most 20 tool calls. `grep` returns at most 50 lines of 300 characters, about 5k tokens. `read_file` returns at most 300 lines, about 4k tokens. Worst case: about 35k + 20 × 5k ≈ 135k tokens |

The limits are named constants in `repo.py` and `agent.py`, with no configuration until
a second provider needs different ones.

## Decision D — the default mode

`--context diff` is the default **[PROPOSED]**, because it is the LLM draft plan's
decided baseline. `repo` is opt-in, until the comparison under "How to decide" in the
repo-access doc settles it.

---

## The seam

```python
# llm/__init__.py — provider-neutral, no SDK imports
@dataclass(frozen=True)
class Tool:
    name: str
    description: str
    schema: dict              # JSON Schema of the arguments

@dataclass(frozen=True)
class ToolCall:
    id: str
    name: str
    arguments: dict | None    # None if the model sent arguments that are not valid JSON

@dataclass(frozen=True)
class ToolResult:
    id: str
    name: str
    text: str
    is_error: bool = False

@dataclass(frozen=True)
class Turn:
    calls: list[ToolCall]
    text: str                 # anything the model said besides its calls
    usage: dict               # prompt, cached and completion tokens, provider-reported
    raw: dict                 # the response as JSON, for result.json

class Conversation(Protocol):
    def step(self) -> Turn: ...
    def add_results(self, results: list[ToolResult]) -> None: ...

def open_conversation(settings, system: str, task: str, tools: list[Tool], cache_key: str) -> Conversation:
    """Chooses the adapter by DOCBOT_LLM_PROVIDER. Only 'mistral' exists for now."""
```

**The adapter keeps the transcript**, in its own provider's format. Mistral needs its
assistant message with `tool_calls` sent back, and Claude will need its content blocks
sent back byte for byte. Neither format leaks into `agent.py`.

## The Mistral adapter

```python
# llm/mistral.py — the only module that imports mistralai
import json
from mistralai.client import Mistral
from mistralai.client.errors import MistralError, NoResponseError

class LLMError(Exception): ...   # lives in llm/__init__.py; the CLI maps it to exit code 1

class MistralConversation:
    def __init__(self, client: Mistral, model: str, system: str, task: str, tools: list[Tool], cache_key: str):
        self._client, self._model, self._cache_key = client, model, cache_key
        self._tools = [{"type": "function",
                        "function": {"name": t.name, "description": t.description, "parameters": t.schema}}
                       for t in tools]
        self._messages: list = [{"role": "system", "content": system}, {"role": "user", "content": task}]

    def step(self) -> Turn:
        try:
            response = self._client.chat.complete(
                model=self._model, messages=self._messages, tools=self._tools,
                tool_choice="any", prompt_cache_key=self._cache_key)
        except (MistralError, NoResponseError) as e:
            raise LLMError(f"mistral: {e}") from e
        message = response.choices[0].message
        self._messages.append(message)
        calls = [ToolCall(c.id, c.function.name, _arguments(c.function.arguments))
                 for c in message.tool_calls or []]
        return Turn(calls, message.content or "", response.usage.model_dump(), response.model_dump())

    def add_results(self, results: list[ToolResult]) -> None:
        for r in results:
            content = f"Error: {r.text}" if r.is_error else r.text
            self._messages.append({"role": "tool", "tool_call_id": r.id, "name": r.name, "content": content})

def _arguments(raw: dict | str) -> dict | None:
    if isinstance(raw, dict):
        return raw
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return None               # agent.py answers with a tool error instead of crashing
```

What the sketch fixes, and what is still to confirm when it is built:

| Item | Status |
|---|---|
| Import path `from mistralai.client import Mistral` (1.x used `from mistralai import Mistral`) | **[EVIDENCE]**, from the package's README |
| `chat.complete` takes `tools`, `tool_choice`, `parallel_tool_calls`, `prompt_cache_key`, `reasoning_effort`, `response_format` | **[EVIDENCE]** |
| `function.arguments` is `dict` or `str` | **[EVIDENCE]**, from `Arguments = Union[Dict[str, Any], str]` |
| `finish_reason` is one of `stop`, `length`, `model_length`, `error`, `tool_calls` | **[EVIDENCE]**. `length` and `model_length` become `needs-human`, "answer cut off" |
| Cached tokens in `usage.prompt_tokens_details.cached_tokens` **[DOCS]** | The SDK's `UsageInfo` has no typed field for it, but allows extra fields **[EVIDENCE]**. So it is read from `usage.model_dump()`, which the adapter already logs whole, and a missing value counts as 0 |
| Error classes `MistralError` (base of `SDKError` and the others) and `NoResponseError` | **[EVIDENCE]** |
| `Mistral(client=…)` takes an `HttpClient`, so tests could pass an `httpx2.Client` with a `MockTransport` | **[UNKNOWN]**. The parameter exists. Whether a plain `httpx2.Client` satisfies the protocol is checked when the adapter's test is written |
| `retry_config` and `timeout_ms` | Exist **[EVIDENCE]**. Set a 120 s timeout and the SDK's retries for 429 and 5xx at implementation time |
| Whether a cache hit happens across DocBot's turns | **[UNKNOWN]**, not guaranteed by Mistral **[DOCS]**. Logged per turn, so the first live run answers it |

**Cache key:** `f"docbot-{sha[:12]}-{step}"`, where `step` is `triage` or `draft`. That is
stable within one run, contains nothing secret, and differs between runs.

**Model:** `DOCBOT_LLM_MODEL=mistral-medium-3-5` **[PROPOSED]**, $1.5 input and $7.5
output per million tokens, 256k context, tool calling **[DOCS]**. Large 3 ($0.5 and
$1.5) is the cheaper comparison run.

## The tools, and what the loop does with them

`repo.py` is the repo-access doc's design with Decision C's caps: `git ls-tree`,
`git grep -n -I -E`, and `git show <sha>:<path>`, plus the `private` deny list from
`doc-map.json`. The submit tools' JSON schemas are the `docbot.triage/1` and
`docbot.proposal/1` shapes from the LLM draft plan.

`agent.run(conversation, handlers, max_calls)` returns either the validated submission
or a reason to stop. For each call it does one of four things:

- **Unknown tool, or arguments that are not JSON:** a tool error that says so.
- **A repo tool:** run it, and log the path and the result size.
- **A submit tool:** validate it. If it is valid, return it. If not, send a tool error
  naming the exact problem: a page not in the table of contents, or a `find` that
  occurs zero times or twice.
- **The limit reached:** stop with `needs-human`, "search did not converge".

## The rest of the pipeline

| Module | What it needs | From |
|---|---|---|
| `ignore.py` | The ignore list from `doc-map.json` at the merge commit → the files that matter. If none are left: `skipped` | LLM draft plan, Decision 1 |
| `manual.py` | Parse `htmlDocPages` from `gruntfile.js` with the same regex as `check-missing-doc.js` (`var htmlDocPages = \[…\]`), and read each English page's headings → a table of contents | LLM draft plan, Decision 1 |
| `edits.py` | Apply `find`/`replace` pairs, where each `find` must occur exactly once | LLM draft plan, Decision 2 |
| `update.py` | The new outcomes (`no-doc-impact`, `no-change`, `needs-human`), several files per commit (`gitlab.commit` already takes a list of actions), the description from both answers. `draft.py` loses `MANUAL_FILE` | LLM draft plan, Decision 4 |
| `cli.py` | `--context diff\|repo`, `--repo PATH`, and narration for the new outcomes | This document |
| `config.py` | `DOCBOT_LLM_PROVIDER`, `DOCBOT_LLM_MODEL`, `MISTRAL_API_KEY`. A missing one exits with code 2 before any call, as today | LLM draft plan, "Configuration and secrets" |
| Prompts | Two system prompts, for triage and drafting, as files in `src/docbot/prompts/`, read with `importlib.resources`. They are reviewed like documentation | This document |

**`result.json`** gets `triage` and `draft` sections. Each one records the provider and
model, and every turn: the tool calls, their arguments, the result sizes, the usage
including cached tokens, and the raw response. There is also a `files_sent` list. The
schema string moves to `docbot.update/2`, since the outcomes change.

## Tests: what runs without a key or the stack

| Test | How |
|---|---|
| `test_ignore.py`, `test_manual.py`, `test_edits.py` | Pure functions. The kind table of `open-test-mr.sh` becomes the parameters of `test_ignore.py` |
| `test_repo.py` | A temporary git repository built in the test: caps, the deny list, a missing sha, a binary file |
| `test_agent.py` | A `FakeConversation` that replays scripted `Turn`s: a valid submission, an invalid one then a fix, bad JSON, an unknown tool, the limit |
| `test_update.py` | The existing `Forge` fake plus `FakeConversation`: every outcome, several files in one commit |
| `test_mistral.py` | The translation both ways: `Tool` → Mistral's schema, a response with `tool_calls` → `Turn`, string arguments, `finish_reason` `length`. Through a mocked transport if `Mistral(client=…)` accepts one, otherwise by building the SDK's response models directly |
| Live smoke test | A `pytest` marker, skipped without `MISTRAL_API_KEY`: one triage conversation on the `ios-department` diff |

## Plumbing

- **Dependency:** `mistralai==3.0.0` in `pyproject.toml`, then `uv lock` and the export to
  `requirements.txt`, as in the README. That adds 11 packages, from 14 to 25, and no
  second HTTP stack **[EVIDENCE]**. Check that the hash-checked install still succeeds in
  the `devinfra` Jenkins image.
- **Key on a laptop:** `tools/docbot/.env`, which already reserves `MISTRAL_API_KEY`.
- **Key in Jenkins:** the LLM draft plan's step 7. Compose passes `tools/docbot/.env` as
  an optional `env_file`, CasC turns it into a `docbot-llm-key` credential, and the
  Jenkinsfile binds it with `withCredentials`, next to `docbot-gitlab-token`. What CasC
  does when the variable is unset is still **[UNKNOWN]**. Check it, because a bad CasC
  value crash-loops Jenkins at boot.
- **Jenkinsfile:** `DOCBOT_LLM_PROVIDER` and `DOCBOT_LLM_MODEL` in `environment`. Once
  `repo` mode is wanted in CI, add `--context repo --repo .`.

## Build order

| # | Step | Needs | Rough size |
|---|---|---|---|
| 1 | `ignore.py`, `manual.py`, `edits.py` and their tests | — | A day |
| 2 | The seam in `llm/__init__.py`, `agent.py`, `FakeConversation`, `test_agent.py` | — | Half a day |
| 3 | `triage.py`, the reworked `draft.py`, the prompts, `update.py` outcomes and description, `test_update.py` | 1, 2 | A day |
| 4 | `llm/mistral.py`, `config.py`, the dependency, `test_mistral.py` | 2 | Half a day |
| 5 | Live smoke test, then `--dry-run` on a laptop against the four scenario merges in `--context diff` | 3, 4, the key | An hour or two, from your terminal |
| 6 | `repo.py`, `--context repo`, `--repo`, `test_repo.py`, the `private` deny list | 2 | Half a day |
| 7 | Key plumbing: compose, CasC, Jenkinsfile | 4 | An hour or two |
| 8 | The fifth scenario, then every scenario in both modes through Jenkins, recorded against expectations with cost per run | 5, 6, 7 | Half a day |

Steps 1 to 4 and 6 need neither the key nor the stack. Step 5 is the first moment
Mistral is called.

---

## What was checked

| # | Check | Result |
|---|---|---|
| 1 | `mistralai` 3.0.0: `chat.complete` parameters | `tools`, `tool_choice`, `parallel_tool_calls`, `response_format`, `reasoning_effort`, `prompt_cache_key` **[EVIDENCE]** |
| 2 | `ToolChoiceEnum` | `auto`, `none`, `any`, `required` **[EVIDENCE]** |
| 3 | `FunctionCall.arguments` | `Union[Dict[str, Any], str]` **[EVIDENCE]** |
| 4 | `ChatCompletionChoice.finish_reason` | `stop`, `length`, `model_length`, `error`, `tool_calls` **[EVIDENCE]** |
| 5 | `ToolMessage` | `role: "tool"`, `tool_call_id`, `name`, `content`, and no error flag **[EVIDENCE]** |
| 6 | `UsageInfo` | `prompt_tokens`, `completion_tokens`, `total_tokens` typed, extra fields allowed. No typed `prompt_tokens_details` **[EVIDENCE]** |
| 7 | `Mistral.__init__` | `api_key`, `server_url`, `client`, `retry_config`, `timeout_ms` among others **[EVIDENCE]** |
| 8 | Package README import path | `from mistralai.client import Mistral` **[EVIDENCE]** |
| 9 | Dependency | `httpx2>=2.13.0`, 25 packages together with DocBot's current 14 **[EVIDENCE]** |
| 10 | `htmlDocPages` in the fixture | A `var htmlDocPages = [...]` literal in `gruntfile.js`, parsed by regex in `check-missing-doc.js` **[EVIDENCE]** |
| 11 | Medium 3.5: context, price, tools | 256k, $1.5 / $7.5, function calling and structured outputs **[DOCS]** |
| 12 | Prompt caching | `prompt_cache_key`, 64-token blocks, cached tokens at 10% of the input price, no guaranteed hit **[DOCS]** |

Not checked: any call to Mistral. Nothing was sent from this session.

## New open questions

Numbering continues from the repo-access doc.

| # | Question | Blocks |
|---|---|---|
| 33 | ~~Is the existing `MISTRAL_API_KEY` on a paid plan or on the free Experiment tier?~~ **Answered 2026-09-30: a paid plan, with usage credits**, so inputs are not used for training by default | — |
| 34 | Does Mistral's data processing agreement confirm EU hosting, and does prompt caching still work under ZDR? | The real repository on Mistral |
