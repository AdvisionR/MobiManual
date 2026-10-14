# DocBot

Keeps the MobiVisor user manual in step with what merges to `main`. Jenkins runs
it after every merge, in the `DocBot` stage of the `Jenkinsfile`. For each merged
merge request it opens at most one docs merge request, for a human to review.
Nothing merges itself.

## Flow

[`update_manual()`](src/docbot/update.py#L32) takes one commit on `main`:

1. **Resolve** the merge request that produced it ([`resolve()`](src/docbot/resolve.py#L30)).
   If it is not a merge to `main`, or is DocBot's own (label `docbot-generated`): `skipped`.
2. **Deduplicate.** If a merge request from `docbot/mr-<iid>` already exists: `exists`.
   A rerun asks no model.
3. **Filter** the diff with the ignore list in `doc-map.json`
   ([`ignore.select()`](src/docbot/drafting/ignore.py#L25)): tests, CI, lock files,
   DocBot itself, the manual. If nothing is left: `skipped`, with no model call. If
   what is left is more than [100,000 characters](src/docbot/update.py#L29) of diff:
   `needs-human`, with no model call.
4. **Draft** (model): does the change make the manual wrong or incomplete, and if
   it does, which pages change and how? If no page needs changing: `no-doc-impact`.
   If none is edited, but one needs a human or the manual lacks a page: `needs-human`.
   See [Drafting](#drafting).
5. **Publish**: one commit on `docbot/mr-<iid>`, and a docs merge request labelled
   `docbot-generated` ([`update.py`](src/docbot/update.py#L89)). Its description
   carries the model's reasons ([`_description()`](src/docbot/update.py#L110)).
   `--dry-run` stops before this step and prints the diff.

The manual is the set of English pages listed in `htmlDocPages` in `gruntfile.js`,
read from GitLab at the merge commit ([`manual.py`](src/docbot/drafting/manual.py#L55)).
DocBot cannot create pages and does not update translations.

`llm/` holds the provider seam and the tool loop, and knows nothing about manuals.
[`mistral.py`](src/docbot/llm/mistral.py) is the only module that imports `mistralai`.
`drafting/` holds what DocBot asks the model, and the tools and checks it needs.
Imports point one way: the top level uses `drafting/`, and `drafting/` uses `llm/`.

## Drafting

[`propose()`](src/docbot/drafting/proposal.py#L115): one conversation, with at most
[35 tool calls](src/docbot/llm/agent.py#L14). The model decides whether the change
affects the manual at all, and if it does, which pages to change and how.

**In.** [`update.py:73`](src/docbot/update.py#L73) hands drafting four things: the
merge request, the diffs that were not ignored, the manual, and the pages the merge
request edited. [`_task()`](src/docbot/drafting/proposal.py#L207) writes them into one
user message:

| Input | Written into the task at | Comes from |
|---|---|---|
| Merge request title, with its `!iid` | [`change.py:6`](src/docbot/drafting/change.py#L6), `mr['title']` | GitLab `GET /repository/commits/:sha/merge_requests` ([`gitlab.py:54`](src/docbot/gitlab.py#L54)), via [`update.py:35`](src/docbot/update.py#L35) |
| Merge request description | [`change.py:6`](src/docbot/drafting/change.py#L6), `mr.get("description")` | the same |
| Diff of each file that is not ignored, with its path | [`change.py:11`](src/docbot/drafting/change.py#L11) | GitLab `GET /merge_requests/:iid/diffs` ([`gitlab.py:61`](src/docbot/gitlab.py#L61)), filtered at [`update.py:59`](src/docbot/update.py#L59) |
| The table of contents: every page in manual order, with its headings | [`manual.py:81`](src/docbot/drafting/manual.py#L81) | `htmlDocPages` in `gruntfile.js`. The pages are read from GitLab at [`update.py:69`](src/docbot/update.py#L69) |
| The marker "already edited in this merge request" | [`manual.py:85`](src/docbot/drafting/manual.py#L85) | manual pages in the diff ([`ignore.py:39`](src/docbot/drafting/ignore.py#L39)) |

The pages' text is not in the task. The model reads and searches what it needs with
these tools:

- `read_page` and `search_manual`, over the manual ([`manual.py`](src/docbot/drafting/manual.py#L33))
- `list_files`, `grep` and `read_file`, over the code at the merge commit
  ([`repo.py`](src/docbot/drafting/repo.py#L20)), unless `--diff-only` is set. They
  answer what the diff does not show: whether a user notices the change at all, and
  what they see.

**Sent.** [`proposal.py:122`](src/docbot/drafting/proposal.py#L122) builds the system
prompt and the task. [`proposal.py:123`](src/docbot/drafting/proposal.py#L123) opens
the conversation with them, the tools, and `submit_proposal`.
[`mistral.py:64`](src/docbot/llm/mistral.py#L64) makes the two texts the first two
messages, and [`mistral.py:68`](src/docbot/llm/mistral.py#L68) sends them, with the
tools, on every turn.

**When a page needs changing.** The [system prompt](src/docbot/drafting/proposal.py#L29)
gives two reasons:
- wrong: a sentence of the page is false once the change is merged.
- missing: the change adds a new thing a reader operates, usable as soon as it is
  merged, on a screen or task the page describes, and the page does not mention it. A
  flag switched on makes what it hid usable; something behind a flag that stays off is
  not usable yet.

A screen or feature that no page covers needs a new page, which DocBot cannot write: the
model names it in `missing_pages`, and must not describe it on an existing page instead.
A change to how something already documented behaves needs an edit only if it makes a
sentence false. A change nobody using the product notices needs none, and the model
then submits no pages.

**Out** ([`submit_proposal`](src/docbot/drafting/proposal.py#L85)):

- `reason`: one or two sentences on what the change does for a user, or that it does
  nothing a user notices. This becomes "Why the manual changes" in the docs merge
  request, and the reason of a `no-doc-impact` outcome.
- `pages`: one entry for each page the model edits, hands to a human, or read and left
  alone. Empty if no page needs changing.
  - `page` and `reason`
  - `decision`: `edit`, `no-change` or `needs-human`
  - `edits`: `find`/`replace` pairs, only with `edit`
- `missing_pages`: pages the change needs and the manual lacks, each with a file name
  (`page`) and what it would describe (`describes`). Listed in the docs merge request.
- `uncertainties`: anything the model is unsure of, such as a screenshot that may be
  out of date.

The outcome follows from the pages ([`update.py:78`](src/docbot/update.py#L78)): a page
edited opens the docs merge request; otherwise a page that needs a human, or a missing
one, is `needs-human`, and anything else `no-doc-impact`. There is no separate decision
field, and no second submit tool for "nothing to change": either would say nothing the
pages do not, and could disagree with them. `missing_pages` is a field of its own
because without it, a change that only needs a new page would edit nothing and end as
`no-doc-impact`, with the new feature undocumented and nobody told.

A proposal is accepted only if it [validates](src/docbot/drafting/proposal.py#L154):
- `reason` is not empty
- every page exists and is answered once
- every `find` matches exactly once
- at most 10 pages are edited
- every missing page is one the manual does not have

If it does not validate, the error goes back to the model, which tries again within
the same call budget.
[`edits.apply()`](src/docbot/drafting/edits.py#L40) tolerates whitespace differences
in `find`, and re-wraps the new lines to the page's own line width. Words that spill
over a broken line join the next line of the same paragraph.

**Checked.** Each run stores the exact system prompt and task in `result.json`
([`proposal.py:134`](src/docbot/drafting/proposal.py#L134)).
- [`test_the_model_reads_the_page_it_chose_then_edits_it`](tests/test_proposal.py#L37):
  the stored texts are the ones the model was given, and a page's text reaches the
  model only through `read_page`.
- [`test_the_task_marks_the_pages_the_merge_request_edited`](tests/test_proposal.py#L64):
  the table of contents marks the pages the author already edited.

## Result

stdout carries one JSON document, `docbot.update/2`. stderr carries the narration,
including the turns and tokens of the conversation. In Jenkins the JSON is archived
as `result.json`. Its `draft` section holds the whole conversation: the system prompt,
the task, and every turn, with each tool call, what it got back, and the token usage.

| `outcome` | When | Docs merge request |
|---|---|---|
| `skipped` | Not a merge to `main`, DocBot's own, or every file ignored | — |
| `exists` | One was already opened for this merge request | The existing one |
| `no-doc-impact` | Drafting found no page to change | — |
| `needs-human` | The diff is too large to send, the conversation ended without a valid answer, or no page was edited and one needs a human or is missing | — |
| `dry-run` | `--dry-run` | —, the diff is in `diff` |
| `opened` | At least one page was edited | Opened |
| `error` | GitLab or the provider was unreachable or refused, or `doc-map.json` or `gruntfile.js` is missing | — |

Exit codes:
- 0: done, including "nothing to do" and `needs-human`
- 1: `error`
- 2: a usage or configuration error, raised before any network call

## Model, performance and cost

**Model:** `mistral-large-4-0` (`DOCBOT_LLM_MODEL`), with `reasoning_effort` `high`
(`DOCBOT_LLM_REASONING_EFFORT`). With nothing sent, Large 4 reasons and Medium 3.5
does not, so the effort is always set. Large 4 has been a public preview since
2026-10-06. It has no dated ID, and the model behind the alias may still change.
Prices per million tokens, half price until about 2026-10-20:
- input: $1.36
- cached input: $0.14
- output: $4.18

The API keeps no state, so every turn resends the whole conversation. Cost grows with
the number of turns, times the size of the diff, the manual and the tool results.
DocBot requests prompt caching, but a hit is not guaranteed. One call took over
120 s, so the timeout is 300 s. Responses 429 and 5xx are retried for up to
5 minutes ([`mistral.py`](src/docbot/llm/mistral.py#L33)).

**Why Large 4 and not Medium 3.5.** Medium is faster, and cheaper than Large 4 at list
price. It misses more of what a draft needs. Medium's figures are from 2026-10-08:

| | Medium 3.5 | Large 4 |
|---|---|---|
| `retire-label`: the Roles table's "retiring" | 0 of 6 | 4 of 4 |
| `kiosk-passcode`: the exit-passcode step | 4 of 6 | 4 of 4 |
| `ios-department`: **Finish** waits for a department | 4 of 6 | 4 of 4 |
| `wifi-policy`: names the missing page | 2 of 4 | 4 of 4 |
| `locations-page`: `needs-human`, page named, no stand-ins | 1 of 4 | 2 of 4 |
| `find` snippets not on the page | 5 of 149 | 0 of 92 |
| Median time, change with doc impact | 8 s | 31 s |

**Not measured yet** for drafting as it is now:
- how often it finds the changes that need a page changed, and stays silent on the
  ones that do not, on the scenarios in `devinfra/scenarios` and the comment kinds of
  `open-test-mr.sh`
- the time and cost per merge. Every merge that reaches the model costs a whole
  drafting conversation, including those that change nothing a user sees.
- Zulip, and MobiVisor's own manual

The model figures come from `docs/docbot-large-4-narrow2.md` and
`docs/docbot-mistral-prototype.md` in the MobiManual repository. The runs are in
`devinfra/.runtime/experiments/large-4-port-2026-10-13/`. DocBot does not compute cost
itself. The token counts are in `result.json`.

## Running

Settings come from the environment ([`config.py`](src/docbot/config.py)):

| Variable | Example |
|---|---|
| `DOCBOT_GITLAB_URL` | `http://gitlab.orb.local` |
| `DOCBOT_PROJECT` | `root/mobivisor-console` |
| `DOCBOT_GITLAB_TOKEN` | A token with `api` scope |
| `MISTRAL_API_KEY` | The model provider's key |
| `DOCBOT_LLM_MODEL` | `mistral-large-4-0` |
| `DOCBOT_LLM_REASONING_EFFORT` | `high`, or `none`. Large 4 and Medium 3.5 accept nothing else |

On a laptop, with [uv](https://docs.astral.sh/uv/), copy `.env.example` to `.env`,
which is gitignored. Then:

```bash
uv run --env-file .env docbot update-manual --sha <merge commit> --repo <clone> --dry-run
uv run pytest                                        # offline: no GitLab, no key
uv run --env-file .env pytest -m live -s -k update   # calls the real model and costs credits
```

- `--sha` defaults to `HEAD` of the working directory.
- `--repo` defaults to the working directory, and must contain the merge commit.
- `--diff-only` drafts without searching the code.
- `-k update` runs each scenario through `update-manual`, against a GitLab replayed
  from git. Results go to `devinfra/.runtime/docbot-results/`.
- `-k zulip` replays zulip/zulip, where `devinfra/` has it set up.
- In CI, the `Jenkinsfile` installs `requirements.txt` into `tools/docbot/.venv`. It
  takes the token and the key from the Jenkins credentials `docbot-gitlab-token` and
  `docbot-llm-key`.
- Dependencies are declared in `pyproject.toml` and pinned in `uv.lock`. CI has no uv,
  so after changing a dependency, export `requirements.txt` for it:
  `uv lock && uv export --frozen --no-dev --no-emit-project --format requirements-txt -o requirements.txt`

## Keeping this directory movable

This directory may later move out of this repository, together with its pipeline.
`docs/docbot-code-location.md` in the MobiManual repository explains why. Four rules
keep that move a plain copy:

- Nothing outside `tools/docbot/` is imported or executed.
- Configuration comes only from variables and flags, never from Jenkins' own variables.
- The only thing read implicitly from the working directory is `git rev-parse HEAD`,
  and `--sha` replaces it.
- stdout carries exactly one JSON document.
