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
4. **Triage** (model): does the change make the manual wrong or incomplete? If not:
   `no-doc-impact`. See [Triage](#triage).
5. **Draft** (model): find the affected pages and propose edits to them. If nothing
   is edited: `no-change` or `needs-human`. See [Drafting](#drafting).
6. **Publish**: one commit on `docbot/mr-<iid>`, and a docs merge request labelled
   `docbot-generated` ([`update.py`](src/docbot/update.py#L95)). Its description
   carries the model's reasons ([`_description()`](src/docbot/update.py#L116)).
   `--dry-run` stops before this step and prints the diff.

The manual is the set of English pages listed in `htmlDocPages` in `gruntfile.js`,
read from GitLab at the merge commit ([`manual.py`](src/docbot/drafting/manual.py#L56)).
DocBot cannot create pages and does not update translations.

`llm/` holds the provider seam and the tool loop, and knows nothing about manuals.
[`mistral.py`](src/docbot/llm/mistral.py) is the only module that imports `mistralai`.
`drafting/` holds what DocBot asks the model, and the tools and checks it needs.
Imports point one way: the top level uses `drafting/`, and `drafting/` uses `llm/`.

## Triage

[`triage()`](src/docbot/drafting/triage.py#L89): one conversation with one tool. The
model reads the whole manual, and answers `doc-impact` only with evidence that points
into it.

**In.** [`update.py:72`](src/docbot/update.py#L72) hands triage four things: the
merge request, the diffs that were not ignored, the manual, and the pages the merge
request edited. [`_task()`](src/docbot/drafting/triage.py#L131) writes them into one
user message, the manual first:

| Input | Written into the task at | Comes from |
|---|---|---|
| Every page in full, under its name, in manual order | [`manual.py:95`](src/docbot/drafting/manual.py#L95) | `htmlDocPages` in `gruntfile.js`. The pages are read from GitLab at [`update.py:69`](src/docbot/update.py#L69) |
| The marker "already edited in this merge request" | [`manual.py:94`](src/docbot/drafting/manual.py#L94) | manual pages in the diff ([`ignore.py:39`](src/docbot/drafting/ignore.py#L39)) |
| Merge request title, with its `!iid` | [`change.py:6`](src/docbot/drafting/change.py#L6), `mr['title']` | GitLab `GET /repository/commits/:sha/merge_requests` ([`gitlab.py:54`](src/docbot/gitlab.py#L54)), via [`update.py:35`](src/docbot/update.py#L35) |
| Merge request description | [`change.py:6`](src/docbot/drafting/change.py#L6), `mr.get("description")` | the same |
| Diff of each file that is not ignored, with its path | [`change.py:11`](src/docbot/drafting/change.py#L11) | GitLab `GET /merge_requests/:iid/diffs` ([`gitlab.py:61`](src/docbot/gitlab.py#L61)), filtered at [`update.py:59`](src/docbot/update.py#L59) |

The manual comes first because it is the same for every merge at one manual version.
The fixture's manual is about 4k tokens. MobiVisor's English manual is about 25k to
29k, which also fits.

**Sent.** [`triage.py:92`](src/docbot/drafting/triage.py#L92) builds the system prompt
and the task. [`triage.py:93`](src/docbot/drafting/triage.py#L93) opens the
conversation with them and one tool, `submit_triage`.
[`mistral.py:64`](src/docbot/llm/mistral.py#L64) makes the two texts the first two
messages, and [`mistral.py:68`](src/docbot/llm/mistral.py#L68) sends them, with the
tool, on every turn. Triage searches no code.

The [system prompt](src/docbot/drafting/triage.py#L33) defines doc impact by evidence of
three kinds:
- `wrong`: a sentence the change makes false, quoted.
- `missing`: a new thing a reader operates, usable as soon as the change is merged, on a
  screen or task a page describes but does not mention it. A flag switched on makes what
  it hid usable; something behind a flag that stays off is not usable yet.
- `new-page`: a screen or feature that no page covers.

A change to how something already documented behaves counts only if it makes a
sentence false.

**Validated** ([`validate()`](src/docbot/drafting/triage.py#L103)): only what can be
looked up. Every page named in the evidence must be in the manual, and its quote on that
page, whitespace aside. A refusal goes back to the model, which tries again.

Whether the evidence is right is the model's call. Four checks that judged it were
tried on 2026-10-13 and left out:
- a label must be on a line the change adds
- a label must not be on a line it removes
- a label must not be only in comments
- a quote must not be a line the author added

They turned a right answer wrong for Large 4 and caught nothing it got wrong.

**Checked.** Each run stores the exact system prompt and task in `result.json`
([`triage.py:100`](src/docbot/drafting/triage.py#L100)).
- [`test_a_valid_answer_comes_back`](tests/test_triage.py#L23): the stored texts are
  the ones the model was given.
- [`test_the_task_holds_the_whole_manual_then_the_change`](tests/test_triage.py#L36):
  the task holds every page, the edited-page marker, the merge request's title and
  description, and the diff, in that order.

**Out** ([`submit_triage`](src/docbot/drafting/triage.py#L69)):

- `decision`: `doc-impact` or `no-doc-impact`
- `reason`: one or two sentences on what the change does for a user. This becomes
  "Why the manual changes" in the docs merge request.
- `evidence`: for `doc-impact`, a list. Each item has:
  - `kind` and `why`
  - `page` and `quote` for `wrong` and `missing`
  - `label` for `missing` and `new-page`

  It is kept in `result.json`, not shown in the docs merge request.

Triage does not choose pages. That is drafting's job.

## Drafting

[`propose()`](src/docbot/drafting/proposal.py#L82): one conversation, with at most
[35 tool calls](src/docbot/llm/agent.py#L14).

**In** ([system prompt](src/docbot/drafting/proposal.py#L26), [task](src/docbot/drafting/proposal.py#L161)):
the same merge request and diff as triage, and the manual's table of contents, plus these tools:

- `read_page` and `search_manual`, over the manual ([`manual.py`](src/docbot/drafting/manual.py#L34))
- `list_files`, `grep` and `read_file`, over the code at the merge commit
  ([`repo.py`](src/docbot/drafting/repo.py#L20)), unless `--diff-only` is set

**Out** ([`submit_proposal`](src/docbot/drafting/proposal.py#L61)):

- `pages`: one entry for each page the model edits, hands to a human, or read and left alone
  - `page` and `reason`
  - `decision`: `edit`, `no-change` or `needs-human`
  - `edits`: `find`/`replace` pairs, only with `edit`
- `uncertainties`: anything the model is unsure of. Examples: a screenshot that may be
  out of date, or a page the manual lacks.

A proposal is accepted only if it [validates](src/docbot/drafting/proposal.py#L120):
- every page exists and is answered once
- every `find` matches exactly once
- at most 10 pages are edited

If it does not validate, the error goes back to the model, which tries again within
the same call budget.
[`edits.apply()`](src/docbot/drafting/edits.py#L40) tolerates whitespace differences
in `find`, and re-wraps the new lines to the page's own line width. Words that spill
over a broken line join the next line of the same paragraph.

## Result

stdout carries one JSON document, `docbot.update/2`. stderr carries the narration,
including the turns and tokens of each conversation. In Jenkins the JSON is archived
as `result.json`. Its `triage` and `draft` sections hold the whole conversation: the
system prompt, the task, and every turn, with each tool call, what it got back, and
the token usage.

| `outcome` | When | Docs merge request |
|---|---|---|
| `skipped` | Not a merge to `main`, DocBot's own, or every file ignored | — |
| `exists` | One was already opened for this merge request | The existing one |
| `no-doc-impact` | Triage answered no | — |
| `no-change` | Drafting edited nothing | — |
| `needs-human` | The diff is too large to send, a conversation ended without a valid answer, or no page was edited and one needs a human | — |
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

**Measured on 2026-10-13** on the fixture: the 24 scenarios in `devinfra/scenarios` in
both modes, and the 5 comment kinds of `open-test-mr.sh`, twice each. That is 106 runs.

- 98 runs had the expected outcome and pages.
- Triage found 53 of 56 changes with doc impact, and answered doc impact for 1 of 48
  without.
- The 8 runs that fell short:
  - `account-expiry`, 3 runs: the change only switches a flag on, and the field it
    shows is in code the diff does not show. Triage stopped it. See "Known limit".
  - `wifi-policy`, 3 runs: an edit to `_settings.md` the scenario does not allow. The
    change supports it: WPA2 Enterprise uses the directory.
  - `ring-duration-documented`, 1 run: triage quoted the sentence the author had
    already corrected. Drafting then changed nothing, so no docs merge request opens.
  - `locations-page`, 1 run: a stand-in sentence about the new page on `_users.md`.
    One more ran out of its 35 calls. Its outcome, `needs-human`, was the expected
    one, but it named no missing page.
- For a change with doc impact: median 31 s, slowest 356 s. $0.015 per merge at
  half price.

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

**Not measured yet:**

- Zulip with this triage. Its help centre is about 225k tokens, and triage sends all of
  it with every change.
- MobiVisor's own manual in triage, about 25k to 29k tokens against the fixture's 4k.

**Known limit:** triage has no repo tools. A change whose effect only the code shows
can therefore stop at triage. `account-expiry` is the example: the prompt says a flag
switched on makes what it hid usable, and triage still stopped it in 3 of 4 runs.

The figures come from `docs/docbot-large-4-narrow2.md` and
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
