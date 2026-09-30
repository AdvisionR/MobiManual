# DocBot — the first model-drafted manual update

**Status:** design, pre-implementation. Written 2026-09-24 against `tools/docbot/` as it
stands after the placeholder step, which works end to end on the stack (see "What was
checked"). Decided the same day:

- the doc map only excludes, and the model picks the pages
- the model sees the diff, not the repository
- one drafting call with repair, not an agent loop
- Mistral, for the prototype only
- outcomes that open no merge request are recorded in `result.json` only

**Relationship to other documents:** this replaces the placeholder in
`tools/docbot/src/docbot/draft.py` (see [docbot-code-location.md](docbot-code-location.md)).
It is roadmap item 2 of `current-state.md`, "Add provider-agnostic AI connection", in its
smallest useful form. From [the foundation doc](mobimanual-docbot-foundation.md) it applies
"Agent behaviour rules" and "Model provider". It knowingly sets aside two **[DECIDED]**
foundation items for now. One is "The doc map" as a hand-maintained code-to-page map,
which also removes the lookup half of the tier-1 gate in [the queue design](docbot-queue-design.md).
The other is that drafting is an agentic loop.

Tags as in the foundation doc: **[DECIDED]**, **[EVIDENCE]**, **[PROPOSED]**,
**[UNKNOWN]**, plus **[DOCS]** as defined in the executor doc.

---

## The question

> Now, plan out the next step where we would incorporate an LLM to write a prototypical
> MobiManual update.

## Short answer

- **Replace only the placeholder.** Everything around it stays: resolving the merge,
  skipping DocBot's own merge requests, the `docbot/mr-<iid>` idempotency, committing
  through the API, and the Jenkins stage. The docs merge request now edits **real manual
  pages** instead of `docbot-changes.md`.
- **The doc map only excludes, and the model picks the pages. [DECIDED 2026-09-24]**
  `doc-map.json` lists the paths that never call for a manual update: tests, CI, DocBot,
  and the manual itself. A merge that touches nothing else ends there, before any model
  call. Everything else goes to two calls:
  1. **Triage** reads the diff next to the manual's table of contents and names the
     affected pages, or none.
  2. **Draft** reads the diff and only those pages, and returns edits.
- **The model sees the diff, not the repository. [DECIDED 2026-09-24]** Its whole input
  is the merge request's title and description, the diff without the ignored files, the
  table of contents, and the text of the pages it picked. It has no tools and no
  repository access.
- **Drafting is one structured call with one repair, not an agent loop yet.**
  **[DECIDED 2026-09-24]** Per page the model answers `edit` (with find-and-replace
  edits), `no-change` or `needs-human`, each with a reason. DocBot applies the edits
  itself.
- **Mistral, behind a small interface, for the prototype only. [DECIDED 2026-09-24]**
  The final provider and model are open.
- **Every call is logged in `result.json`**: prompt, raw response, model and token usage.
  This is the foundation's "log every verdict and every draft", and the triage log is
  also what a future code-to-page map would be built from.
- **The test merge requests need real changes.** Four scenario merge requests with real
  behaviour changes and expected outcomes start the evaluation corpus.
- **This runs against the fixture only.** The fixture may go to Mistral. The real
  repository stays blocked on question 10, data-governance sign-off.

---

## What changes, and what does not

```
update-manual                   unchanged: resolve, skip docbot-generated, docbot/mr-<iid>
  │
  ├── ignore.py    pure    changed files − doc-map ignore list → what matters (nothing left → skipped)
  ├── context      API     MR title and description, /diffs, gruntfile.js and each page at the merge sha
  ├── manual.py    pure    htmlDocPages + each page's headings → table of contents
  ├── triage.py    model   diff + table of contents → docbot.triage/1: pages, or none
  ├── draft.py     model   diff + the picked pages' text → docbot.proposal/1
  ├── edits.py     pure    proposal + page texts → new page texts, or an error to repair
  └── publish      API     one commit with every edited page; MR description from both answers
```

Two steps talk to a model, both through one interface. Everything in between is pure and
unit-tested: choosing what matters, building the table of contents, validating both
answers, and applying the edits.

---

## Decision 1 — the doc map only excludes; the model picks the pages

| Option | Verdict |
|---|---|
| A hand-maintained code-to-page map (the foundation's doc map, and the fixture's `doc-map.json` until now) | **Rejected for now. [DECIDED 2026-09-24]** Someone has to maintain it, and every console refactor makes entries stale. A stale entry hands the model the wrong page with full confidence. See [Why a map may come back](#why-a-code-to-page-map-may-come-back) |
| Send the model the whole English manual, in one call | **Rejected.** It fits the fixture's eight pages. The real manual builds to 166 KB of HTML, and that cost would repeat on every merge |
| Derive the page from the naming convention (`routes.js` → `_<route>.md`) | **Not now.** Getting from a changed file to its route takes more than the path. It could be added later as a hint to triage |
| **The model picks from a table of contents** | **Chosen. [DECIDED 2026-09-24]** The input stays small at the real manual's size. It is the foundation's tier-2 gate, and it also covers changes that aren't excluded but don't matter, such as an internal refactor |

**The ignore list** (`doc-map.json`, `ignore`) decides only whether a merge reaches the
model. If every changed file is ignored, the outcome is `skipped` and no call is made.
Otherwise the ignored files are dropped from the diff the model sees, with one exception:
manual pages the merge request edited itself are named in the table of contents as
"already edited in this merge request". This keeps the queue design's `already_served`
refinement without a map, and the fixture's `both` kind tests it.

**The table of contents** is `htmlDocPages` from `gruntfile.js` at the merge commit, read
the way `check-missing-doc.js` reads it, with each English page's headings. It lists the
eight content pages in manual order and leaves out `search.md` and `break.md` by
construction **[EVIDENCE]**. Build machinery can never be picked.

**The triage answer**, validated before anything else happens:

```json
{
  "schema": "docbot.triage/1",
  "decision": "doc-impact | no-doc-impact",
  "pages": [ { "page": "_enrollment_ios.md", "reason": "the wizard gains a step" } ],
  "reason": "one sentence on the merge request as a whole"
}
```

Every page must be in the table of contents. `doc-impact` needs at least one page, and
`no-doc-impact` allows none. At most three pages go on to drafting, a guard for the
prototype **[PROPOSED]**. If more are picked, the outcome is `needs-human`, "too broad for
one draft". The contract for what counts as user-facing (question 7) will eventually live
in the triage prompt.

**English only.** Pages in `tr/` and `de/` are listed as translation debt in the
description. Question 1 is still open.

**Deferred with the map: page classes.** Nothing now stops triage from picking
`cover_page.md` or `chapter1.md`, which the foundation classes as `human-only`. For the
prototype, the human reviewer is the safeguard. Before the real repository, question 27
has to say which pages DocBot may never edit, and where that is recorded.

### Why a code-to-page map may come back

Letting the model decide is the right call while there is no data. A map may still
return later, **as an output of the pilot rather than an input maintained by hand**
**[PROPOSED]**:

- **The data for it builds up anyway.** Every triage answer is logged: which changed
  paths led to which pages, and whether the reviewer merged or closed the resulting docs
  merge request. After a few weeks, that log is what a map is made of.
- **A generated and reviewed map differs from per-merge decisions in three ways.**
  - It is reviewable: a wrong link shows up in a diff and is fixed once.
  - It is reproducible: the same change leads to the same pages, whatever the model
    version or prompt.
  - It captures links the model cannot see from a diff and a table of contents. For
    example, `server/protocol/dep/` affects the enrollment page, but the model sees
    neither the route table nor the call graph.
- **It would be a hint, not a gate.** Triage would receive the known links for the
  changed paths and still decide. That keeps the model's recall on what the map does not
  know yet.

## Decision 2 — how the model edits: one structured call

| Option | Verdict |
|---|---|
| The model returns whole pages | **Rejected.** It breaks "prefer minimal edits", and a reviewer has to diff prose the model re-flowed |
| The model returns a unified diff | **Rejected.** A diff only applies with exact line numbers and context. A find-and-replace edit only needs an exact snippet, and when it fails, the reason is easy to tell the model |
| **Find-and-replace edits plus a decision per page, in one call** | **Chosen. [DECIDED 2026-09-24]** |
| An agent loop with file tools (foundation, "Agent behaviour rules", **[DECIDED]**) | **Deferred, not rejected.** The loop's value is iterating against a build it must pass, and searching the manual for terminology. The fixture has no build to pass (`grunt web_docs` only reports what it would build), and it would also go beyond "the diff suffices". Revisit when `validate` exists. The proposal is what the loop's final tool call would submit, so the loop will wrap this step, not replace it |

```json
{
  "schema": "docbot.proposal/1",
  "pages": [
    { "page": "_enrollment_ios.md",
      "decision": "edit | no-change | needs-human",
      "edits": [ { "find": "exact text from the page", "replace": "new text" } ],
      "reason": "what in the diff makes this necessary" }
  ],
  "uncertainties": ["anything the model could not tell from the diff"]
}
```

- **Validation.** Every page named must be one that triage picked. `edits` are required
  for `edit` and forbidden otherwise. Each `find` must occur exactly once in its page.
- **Repair, for both calls.** If the JSON is invalid, names an unknown page, or has a
  `find` that does not match, DocBot sends one follow-up naming the exact problem. If
  triage still fails, the outcome is `error`. If a draft page still fails, that page
  becomes `needs-human`. At most two calls each, four in the worst case.
- **Rules in the system prompt**, taken from the foundation's "Agent behaviour rules" and
  "Prose register":
  - Describe only what the diff shows, and never invent behaviour.
  - Make the smallest edit that makes the page true.
  - Write UI labels the way the manual does (`**Enrollment > iOS**`).
  - Put doubts in `uncertainties` rather than guessing.
  - "No change needed" and "needs a human, screenshot may be stale" are both
    first-class answers.

## Decision 3 — the provider seam

```python
class LLM(Protocol):
    def complete(self, system: str, messages: list[dict], schema: dict) -> Completion: ...
    # Completion: the text, the model that answered, token usage
```

Each adapter uses its provider's structured-output feature if the provider has one.
DocBot validates the JSON itself either way, so no adapter is trusted to enforce the
schema. The adapter is the only module that imports its provider's SDK, the same rule
`gitlab.py` follows for `httpx2`.

| Option | Verdict |
|---|---|
| **Own small interface, one SDK adapter per provider** | **Chosen. [PROPOSED]** Each adapter is a few dozen lines, and the SDK handles retries and timeouts |
| An abstraction library (LiteLLM) | **Rejected for now.** 55 packages installed, against 14 to 18 for a single provider's SDK **[EVIDENCE]**. That adds a layer between DocBot and every provider, which has to keep up with each of their APIs |
| Raw HTTP per provider | **Rejected.** See "Dependencies" in the code-location doc: the SDKs already handle retries, rate limits and streaming |
| Two adapters now | **Rejected.** A/B testing needs a corpus to compare on (Decision 5). One adapter is enough to prove the seam |

**Mistral, for the prototype only. [DECIDED 2026-09-24]** It is the key that exists, and
`tools/docbot/.env.example` reserves `MISTRAL_API_KEY`. The final provider and model are open
(question 24). The foundation doc's "Either OpenAI or Anthropic" is neither confirmed nor
replaced by this choice. What comes with it:

- `mistralai` uses `httpx` 0.28.1 and OpenTelemetry **[EVIDENCE]**, from the
  code-location doc, while DocBot uses `httpx2`. So DocBot carries two HTTP stacks, with
  each confined to its one module: `gitlab.py`, and `llm/mistral.py` through the SDK.
- Which structured-output mode `mistralai` offers, and which model to use, are checked
  against the current SDK and model list at implementation time, not written down here.
  The model is configuration (`DOCBOT_LLM_MODEL`).

## Decision 4 — outcomes, and what the docs merge request says

| Outcome | When | Merge request |
|---|---|---|
| `opened` | At least one page has an applied edit | One commit on `docbot/mr-<iid>` with every edited page |
| `no-doc-impact` | Triage found no affected page | None |
| `no-change` | Triage picked pages, and drafting found nothing to change on any of them | None |
| `needs-human` | No page edited, and at least one `needs-human` | None |
| `skipped` | Not a merge, DocBot's own merge request, or every changed file is ignored | None, as today |
| `exists`, `error` | As today | As today |

Outcomes without a merge request are recorded in `result.json` only
**[DECIDED 2026-09-24]**. `no-doc-impact` and `no-change` stay separate on purpose: the
first says triage saw nothing, the second says triage was wrong or too cautious. For the
research log, that difference matters.

The description is where the model's reasoning reaches a reviewer:

```
Drafted by DocBot (<provider>/<model>) for !12: <url>

Why these pages (triage)
- _enrollment_ios.md: <reason>

Edited
- _enrollment_ios.md: <reason>

Needs a human
- _policies_kiosk.md: screenshots/_kiosk_mode_1.png may show the old dialog

Uncertain
- <each item from the proposal>

Not updated: tr/, de/ (translation debt, question 1)

Nothing merges itself: review it, then merge or close.
```

**A known gap.** Outcomes without a merge request leave nothing the existing check can
find, so a rebuild asks the model again. That is acceptable against the fixture. The
queue's `docbot-processed` label closes the gap, as it closes the coalescing gap.

Per-page edits also make the "two open docs merge requests" conflict rarer: they now
conflict only when both touch the same page. Rarer is not never, so serialisation is
still the step after this one.

## Decision 5 — test scenarios with real changes

`open-test-mr.sh` appends a comment to each kind's file **[EVIDENCE]**. Every kind the
doc map does not ignore should therefore come back `no-doc-impact`. That is a useful test
of silence, and useless for testing drafting. Four scenarios, each a patch plus a merge
request title and description, with an expected outcome:

| Scenario | Change | Expected triage | Expected draft |
|---|---|---|---|
| `ios-department` | The iOS wizard's profile gains a department the device is assigned to | `_enrollment_ios.md` | A new step between the current steps 3 and 4. `tr`/`de` listed as debt |
| `kiosk-passcode` | Kiosk mode gains its own exit passcode | `_policies_kiosk.md` | The sentence "Leaving kiosk mode requires the device passcode." is corrected, not just added to. `_kiosk_mode_1.png` is flagged as possibly stale |
| `devices-filter` | The device list gains a compliance filter | `_devices.md`, and possibly `_devices_id.md` | One sentence more on `_devices.md`. If triage also picked `_devices_id.md`, that page comes back `no-change`. Record which one happened |
| `refactor` | The users controller's reload is split into helpers, with nothing visible changing | `no-doc-impact` | — This proves silence at the model tier |

**Built 2026-09-24**, in `devinfra/scenarios/<name>.patch`. Run them with
`./scripts/open-test-mr.sh <name> --merge`, where `ios-department` is the default. Each
patch is `git format-patch` output:

- **The MR text comes from the commit.** Its message is the merge request's title and
  description, written the way a developer would write them, without mentioning the
  manual.
- **The expectation cannot leak.** The `Expected:` line sits below the `---`, which
  `git am` leaves out of the commit message, so it never reaches the description the
  model reads. For all four patches, the applied commit message contains no `Expected:`
  **[EVIDENCE]**.
- **The patches survive earlier test runs.** `git am -3` applies all four even to a
  `main` that already carries a comment stamp, as GitLab's does after a `code` run
  **[EVIDENCE]**.
- **Already-merged scenarios are caught.** `git am` treats an already-applied patch as
  "No changes", exits 0 and makes no commit **[EVIDENCE]**. The script checks for that
  itself and asks for a re-seed.

Together with the comment kinds expected to come back `no-doc-impact`, the scenarios
are the first evaluation corpus. Replaying them offline is how prompt and provider
changes will get compared.

## Configuration and secrets

| Setting | Home |
|---|---|
| `DOCBOT_LLM_PROVIDER`, `DOCBOT_LLM_MODEL` | The Jenkinsfile's environment, like the other `DOCBOT_*` settings. Deployment config |
| `MISTRAL_API_KEY`, the provider's own variable name | Secret. In Jenkins, a `docbot-llm-key` credential bound with `withCredentials`. On a laptop, `tools/docbot/.env` |

A missing setting still fails with exit code 2 before any call, naming the variable, as
`config.py` does today.

**The key lives in `tools/docbot/.env`, next to the code that reads it.
[DECIDED 2026-09-24]** That file is gitignored twice. The MobiManual repository's
`.gitignore` covers it here. `tools/docbot/.gitignore` covers it in the fixture, which
`seed-project.sh` copies into a fresh repository and pushes. Only the second rule
applies to that push. A simulated push commits `.env.example` and leaves `.env` out
**[EVIDENCE]**. On a laptop, `uv run --env-file .env` loads it, and variables exported
in the shell win over the file **[EVIDENCE]**. So `config.py` keeps reading only the
environment. It never goes in `devinfra/.env`, which is committed to git **[EVIDENCE]**.

**In `devinfra`, Jenkins gets the key from the same file.** Compose passes
`demo-repo/tools/docbot/.env` to the Jenkins container as an optional `env_file`
(Compose v5.1.2 here, **[DOCS]** for `required: false`), and CasC turns
`MISTRAL_API_KEY` into the `docbot-llm-key` credential **[PROPOSED]**, for step 7. How
CasC behaves when that variable is unset is **[UNKNOWN]**. Check it before relying on
it, since a bad CasC value crash-loops Jenkins at boot (see the header of
`casc/jenkins.yaml`). One side effect to know about: `seed-project.sh` copies the whole
fixture into `devinfra/.runtime/seed-repo/` before pushing. The copy of `.env` is not
pushed, but it does stay on disk there, in a directory that is itself gitignored.

## Logging

`result.json` gains `triage` and `draft` sections. Each holds the provider, the model,
and for each attempt the prompt, the raw response and the token usage, followed by the
validated answer. It stays one document, per the stdout contract, and Jenkins already
archives it. The key never appears in it. The prompts contain the diff, which is fine for
the fixture and is exactly what question 10 is about for the real repository.

---

## Module layout

```
tools/docbot/src/docbot/
  ignore.py         new    pure: doc-map ignore list -> the changed files that matter, and manual pages already edited
  manual.py         new    pure: htmlDocPages + page headings -> table of contents
  triage.py         new    model call 1: prompt, docbot.triage/1 validation, one repair
  draft.py          reworked  model call 2: prompt, docbot.proposal/1 validation, one repair
  edits.py          new    pure: apply find-and-replace edits
  llm/__init__.py   new    the LLM protocol, Completion, and choosing an adapter by DOCBOT_LLM_PROVIDER
  llm/mistral.py    new    the only module importing mistralai
  update.py         reworked  the new outcomes, several files per commit, the description
  config.py         extended  provider, model, key
tests/
  test_ignore.py    the open-test-mr.sh kind table as parameters: ignored or passed on
  test_manual.py
  test_edits.py
  test_update.py    extended with a fake LLM
```

## Sequenced steps

| # | Step | Depends on | Rough size |
|---|---|---|---|
| 1 | `ignore.py`, `manual.py` and their tests | — | Half a day. No model, no stack |
| 2 | `edits.py`, answer validation, and their tests | — | Half a day. No model, no stack |
| 3 | ~~The scenarios in `devinfra`~~ **Done 2026-09-24** | — | The pushes run from your terminal |
| 4 | LLM seam, the Mistral adapter, config | — | Half a day |
| 5 | `triage.py` with fake-LLM tests | 1, 4 | Half a day |
| 6 | `draft.py`, the outcomes, the description, logging | 2, 5 | A day |
| 7 | Key plumbing: compose `env_file` from `tools/docbot/.env`, CasC credential, Jenkinsfile binding | 4 | An hour or two |
| 8 | Run the scenarios and the comment kinds: laptop dry-run first, then through Jenkins. Record each outcome against its expectation | 3, 6, 7 | Half a day |

Steps 1, 2 and 3 need neither a key nor the stack.

---

## What was checked

| # | Check | Result |
|---|---|---|
| 1 | The placeholder step on the re-seeded stack | Main #1, the seed push: `skipped`, not a merge. Main #2, the merge of !1: `opened` docs MR !2 from `docbot/mr-1`. Main #3, the merge of !2: `skipped` as DocBot's own. The venv was reused on #3 **[EVIDENCE]** |
| 2 | Size of the fixture's English pages and controllers | 141 lines together. Each page is 1 to 17 lines **[EVIDENCE]** |
| 3 | What `htmlDocPages` lists | The eight content pages in manual order. `search.md` and `break.md` are left out **[EVIDENCE]** |
| 4 | What `open-test-mr.sh` changes | A comment per kind file **[EVIDENCE]** |
| 5 | Does `GET /repository/commits/:sha/merge_requests` include each merge request's `description`? | Yes, so no extra call is needed **[EVIDENCE]** |
| 6 | Packages installed by `litellm`, `anthropic`, `openai`, `mistralai` (`uv pip compile`, Python 3.13) | 55, 15, 14 and 18 **[EVIDENCE]** |
| 7 | Is `devinfra/.env` tracked? | Yes **[EVIDENCE]** |

Not checked: a rebuild of !1's merge commit reporting `exists`. Run from this editor
session, Python gets "No route to host" to the stack, like git does. DocBot reported it
correctly as `error`, exit code 1.

## New open questions

Numbering continues from the code-location doc.

| # | Question | Blocks |
|---|---|---|
| 24 | Which provider and model for the pilot? The prototype uses Mistral (**answered for the prototype 2026-09-24**). The final choice belongs with question 10 | The pilot, not the prototype |
| 25 | ~~Does sending the synthetic fixture to an external model need approval?~~ **Answered 2026-09-24:** the fixture may go to Mistral. The model gets the diff, never repository access | — |
| 26 | ~~Before `report` exists, where does "needs a human" show?~~ **Answered 2026-09-24: in `result.json` only.** A note on the source merge request comes with `report` | — |
| 27 | Without page classes, which pages must DocBot never edit (the foundation's `human-only`: the cover page, chapter 1, anything contractual), and where is that recorded? | The real repository. In the prototype, the reviewer is the safeguard |
