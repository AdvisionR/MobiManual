# DocBot

Keeps the MobiVisor user manual in step with what merges to `main`. Jenkins runs
it after every merge, in the `DocBot` stage of the `Jenkinsfile`. For each merged
merge request it opens at most one docs merge request, for a human to review.
Nothing merges itself.

## Flow

[`update_manual()`](src/docbot/update.py#L34) takes one commit on `main`:

1. **Resolve** the merge request that produced it ([`resolve()`](src/docbot/resolve.py#L30)).
   If it is not a merge to `main`, or is DocBot's own (label `docbot-generated`): `skipped`.
2. **Deduplicate.** If a merge request from `docbot/mr-<iid>` already exists: `exists`.
   A rerun asks no model.
3. **Filter** the diff with the ignore list in `doc-map.json`
   ([`ignore.select()`](src/docbot/drafting/ignore.py#L25)): tests, CI, lock files,
   DocBot itself, the manual. If nothing is left: `skipped`, with no model call. If
   what is left is more than [100,000 characters](src/docbot/update.py#L31) of diff:
   `needs-human`, with no model call.
4. **Draft** (model): does the change make the manual wrong or incomplete, and if
   it does, which pages change and how, and which pages does the manual lack? Those
   it then writes. If no page needs changing: `no-doc-impact`. If none is edited or
   created, but one needs a human: `needs-human`. See [Drafting](#drafting).
5. **Publish**: one commit on `docbot/mr-<iid>`, and a docs merge request labelled
   `docbot-generated` ([`update.py`](src/docbot/update.py#L103)). The commit holds
   the edited pages, the created ones, and `gruntfile.js` with the created pages added
   to `htmlDocPages`. The description carries the model's reasons
   ([`_description()`](src/docbot/update.py#L123)).
   `--dry-run` stops before this step and prints the diff.

The manual is the set of English pages listed in `htmlDocPages` in `gruntfile.js`,
read from GitLab at the merge commit ([`manual.py`](src/docbot/drafting/manual.py#L56)).
DocBot does not update translations: the pages it edits and creates are English only.

`llm/` holds the provider seam and the tool loop, and knows nothing about manuals.
[`mistral.py`](src/docbot/llm/mistral.py) is the only module that imports `mistralai`.
`drafting/` holds what DocBot asks the model, and the tools and checks it needs.
Imports point one way: the top level uses `drafting/`, and `drafting/` uses `llm/`.

## Drafting

[`propose()`](src/docbot/drafting/proposal.py#L164): one conversation, with at most
[35 tool calls](src/docbot/llm/agent.py#L19). The model decides whether the change
affects the manual at all, and if it does, which pages to change and how.

**In.** [`update.py:75`](src/docbot/update.py#L75) hands drafting four things: the
merge request, the diffs that were not ignored, the manual, and the pages the merge
request edited. [`_task()`](src/docbot/drafting/proposal.py#L335) writes them into one
user message:

| Input | Written into the task at | Comes from |
|---|---|---|
| Merge request title, with its `!iid` | [`change.py:6`](src/docbot/drafting/change.py#L6), `mr['title']` | GitLab `GET /repository/commits/:sha/merge_requests` ([`gitlab.py:54`](src/docbot/gitlab.py#L54)), via [`update.py:37`](src/docbot/update.py#L37) |
| Merge request description | [`change.py:6`](src/docbot/drafting/change.py#L6), `mr.get("description")` | the same |
| Diff of each file that is not ignored, with its path | [`change.py:11`](src/docbot/drafting/change.py#L11) | GitLab `GET /merge_requests/:iid/diffs` ([`gitlab.py:61`](src/docbot/gitlab.py#L61)), filtered at [`update.py:61`](src/docbot/update.py#L61) |
| The table of contents: every page in manual order, with its headings | [`manual.py:111`](src/docbot/drafting/manual.py#L111) | `htmlDocPages` in `gruntfile.js`. The pages are read from GitLab at [`update.py:71`](src/docbot/update.py#L71) |
| The marker "already edited in this merge request" | [`manual.py:115`](src/docbot/drafting/manual.py#L115) | manual pages in the diff ([`ignore.py:39`](src/docbot/drafting/ignore.py#L39)) |

The pages' text is not in the task. The model reads and searches what it needs with
these tools:

- `read_page` and `search_manual`, over the manual ([`manual.py`](src/docbot/drafting/manual.py#L34))
- `list_files`, `grep` and `read_file`, over the code at the merge commit
  ([`repo.py`](src/docbot/drafting/repo.py#L20)). They answer what the diff does not
  show: whether a user notices the change at all, and what they see.

**Sent.** [`proposal.py:173`](src/docbot/drafting/proposal.py#L173) builds the system
prompt and the task. [`proposal.py:175`](src/docbot/drafting/proposal.py#L175) opens
the conversation with them, the tools, and `submit_proposal`.
[`mistral.py:62`](src/docbot/llm/mistral.py#L62) makes the two texts the first two
messages, and [`mistral.py:66`](src/docbot/llm/mistral.py#L66) sends them, with the
tools, on every turn.

**When a page needs changing.** The [system prompt](src/docbot/drafting/proposal.py#L38)
gives two reasons:
- wrong: a sentence of the page is false once the change is merged.
- missing: the change adds a new thing a reader operates, usable as soon as it is
  merged, on a screen or task the page describes, and the page does not mention it. A
  flag switched on makes what it hid usable; something behind a flag that stays off is
  not usable yet.

A screen or feature that no page covers needs a new page: the model names it in
`missing_pages`, and writes it once its proposal is accepted (see
[Writing new pages](#writing-new-pages)). It must not describe it on an existing page
instead, and must not name a new page for something that belongs on a page the manual
has, such as a new field on a screen a page describes. In MobiVisor, a console screen's
page is named after its route, because that is the page the screen's **Help** link
opens: `/policies/kiosk` has `_policies_kiosk.md`
([`PAGE_NAMES`](src/docbot/drafting/proposal.py#L31)). A change to how something already documented behaves needs an edit only if it makes a
sentence false. A change nobody using the product notices needs none, and the model
then submits no pages.

**Out** ([`submit_proposal`](src/docbot/drafting/proposal.py#L96)):

- `reason`: one or two sentences on what the change does for a user, or that it does
  nothing a user notices. This becomes "Why the manual changes" in the docs merge
  request, and the reason of a `no-doc-impact` outcome.
- `pages`: one entry for each page the model edits, hands to a human, or read and left
  alone. Empty if no page needs changing.
  - `page` and `reason`
  - `decision`: `edit`, `no-change` or `needs-human`
  - `edits`: `find`/`replace` pairs, only with `edit`
- `missing_pages`: pages the change needs and the manual lacks, each with a file name
  (`page`) and what it will describe (`describes`). The model writes them next.
- `uncertainties`: anything the model is unsure of, such as a screenshot that may be
  out of date.

The outcome follows from the pages ([`update.py:81`](src/docbot/update.py#L81)): a page
edited or created opens the docs merge request; otherwise a page that needs a human, or
a missing one nobody wrote, is `needs-human`, and anything else `no-doc-impact`. There
is no separate decision field, and no second submit tool for "nothing to change":
either would say nothing the pages do not, and could disagree with them.

A proposal is accepted only if it [validates](src/docbot/drafting/proposal.py#L218):
- `reason` is not empty
- every page exists and is answered once
- every `find` matches exactly once
- at most 10 pages are edited
- no missing page is named like a page that exists, because a file that exists cannot
  be created. Whether a page is really missing is the model's call: a page under
  another name, such as `_users_groups.md` next to `_groups_users.md`, is not caught.

If it does not validate, the error goes back to the model, which tries again within
the same call budget.
[`edits.apply()`](src/docbot/drafting/edits.py#L40) tolerates whitespace differences
in `find`, and re-wraps the new lines to the page's own line width. Words that spill
over a broken line join the next line of the same paragraph.

## Writing new pages

A proposal that names pages in `missing_pages` does not end the conversation. Its
accepted `submit_proposal` gets the task of writing them back
([`WRITE_PAGES`](src/docbot/drafting/proposal.py#L147)), and only then does the model
get a second submit tool, `submit_new_pages`
([`proposal.py:187`](src/docbot/drafting/proposal.py#L187)), with
[35 more tool calls](src/docbot/llm/agent.py#L19). It keeps the conversation, and so
the code and pages it has read.

The decision comes first, on its own:
- the model says which pages are missing, and what each will describe, before it writes
  any, in the same answer as its edits to the pages the manual has
- those edits are accepted whatever happens to the new pages
- the model cannot see a tool that creates pages until it has said which ones are missing

**Out** ([`submit_new_pages`](src/docbot/drafting/proposal.py#L127)), for each page
named in `missing_pages`:
- `decision`: `create`, or `needs-human` for a page the model cannot write from what it
  knows
- `after`: the page it follows in the manual's order
- `text`: the whole page, with `create`
- `reason`

`uncertainties` names the screenshots the new pages need, among anything else.

It is accepted only if it [validates](src/docbot/drafting/proposal.py#L269): every
missing page answered once and no other, a title on every page, `after` a page in the
manual, and no images, because no screenshot of a new screen exists yet. If writing
stops without a valid answer, the edits still go out, and the missing pages are listed
under "Needs a human".

**Published** with the edits. A created page joins `htmlDocPages` in `gruntfile.js`
right after its `after` page ([`register()`](src/docbot/drafting/manual.py#L63)), so the
build publishes it and `scripts/check-missing-doc.js` finds it registered. The list is
rewritten one quoted page per line, as it is laid out. If that would change anything
else, such as a comment in the list, the page is still created, and the docs merge
request asks the reviewer to register it by hand. The page is English only: the check
then reports it missing in the other languages, as translation debt.

**Checked.** Each run stores the exact system prompt and task in `result.json`
([`proposal.py:199`](src/docbot/drafting/proposal.py#L199)).
- [`test_the_model_reads_the_page_it_chose_then_edits_it`](tests/test_proposal.py#L52):
  the stored texts are the ones the model was given, and a page's text reaches the
  model only through `read_page`.
- [`test_the_task_marks_the_pages_the_merge_request_edited`](tests/test_proposal.py#L85):
  the table of contents marks the pages the author already edited.
- [`test_a_missing_page_is_written_only_after_the_proposal_is_accepted`](tests/test_proposal.py#L98):
  `submit_new_pages` is added only once the proposal is accepted, and the writing goes
  on in the same conversation.
- [`test_a_page_the_manual_lacks_is_created_and_joins_the_page_list`](tests/test_update.py#L122):
  the commit creates the page and adds it to `htmlDocPages`.

## Result

stdout carries one JSON document, `docbot.update/3`. stderr carries the narration,
including the turns and tokens of the conversation. In Jenkins the JSON is archived
as `result.json`. Its `draft` section holds the whole conversation: the system prompt,
the task, and every turn, with each tool call, what it got back, and the token usage.

| `outcome` | When | Docs merge request |
|---|---|---|
| `skipped` | Not a merge to `main`, DocBot's own, or every file ignored | — |
| `exists` | One was already opened for this merge request | The existing one |
| `no-doc-impact` | Drafting found no page to change | — |
| `needs-human` | The diff is too large to send, the conversation ended without a valid answer, or no page was edited or created and one needs a human | — |
| `dry-run` | `--dry-run` | —, the diff is in `diff` |
| `opened` | At least one page was edited or created | Opened |
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
5 minutes ([`mistral.py`](src/docbot/llm/mistral.py#L35)).

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

**Measured on 2026-10-14** on the fixture: the 30 scenarios in `devinfra/scenarios` and
the 5 comment kinds of `open-test-mr.sh`, twice each. That is 70 runs.

- All 70 had the expected outcome, and edited and created the expected pages. It found
  all 40 changes that needed a page changed or created, and stayed silent on all 30
  that did not.
- On reading, 68 are right. In both runs of `commands-tab-rework`, the draft renames
  **Retry** right, but also describes the history's paging and its loading and empty
  states, which the scenario counts as below the manual's level of detail.
- It created `_locations.md` and `_policies_wifi.md` in both of their runs, each
  registered after the right page, and wrote nothing about them on other pages.
- $0.52 for the 70 runs at half price. A change that needs no page changed: median
  14 s, $0.004. One that does: median 24 s, slowest 179 s, $0.011.

**Not measured yet:** Zulip, and MobiVisor's own manual.

The model figures come from `docs/docbot-large-4-narrow2.md` and
`docs/docbot-mistral-prototype.md` in the MobiManual repository, and the measurement
above from `docs/docbot-drafting-alone.md`. The runs are in
`devinfra/.runtime/experiments/`. DocBot does not compute cost itself. The token counts
are in `result.json`.

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
