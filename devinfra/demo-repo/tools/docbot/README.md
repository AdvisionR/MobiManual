# DocBot

Keeps the MobiVisor user manual in step with what merges to `main`. Jenkins runs
it after every merge, in the `DocBot` stage of the `Jenkinsfile`. For each merged
merge request it opens at most one docs merge request, for a human to review.
Nothing merges itself.

## Flow

[`update_manual()`](src/docbot/update.py#L30) takes one commit on `main`:

1. **Resolve** the merge request that produced it ([`resolve()`](src/docbot/resolve.py#L30)).
   If it is not a merge to `main`, or is DocBot's own (label `docbot-generated`): `skipped`.
2. **Deduplicate.** If a merge request from `docbot/mr-<iid>` already exists: `exists`.
   A rerun asks no model.
3. **Filter** the diff with the ignore list in `doc-map.json`
   ([`ignore.select()`](src/docbot/drafting/ignore.py#L25)): tests, CI, DocBot itself,
   the manual. If nothing is left: `skipped`, with no model call.
4. **Triage** (model): does the change make the manual wrong or incomplete? If not:
   `no-doc-impact`. See [Triage](#triage).
5. **Draft** (model): find the affected pages and propose edits to them. If nothing
   is edited: `no-change` or `needs-human`. See [Drafting](#drafting).
6. **Publish**: one commit on `docbot/mr-<iid>`, and a docs merge request labelled
   `docbot-generated` ([`update.py`](src/docbot/update.py#L89)). Its description
   carries the model's reasons ([`_description()`](src/docbot/update.py#L110)).
   `--dry-run` stops before this step and prints the diff.

The manual is the set of English pages listed in `htmlDocPages` in `gruntfile.js`,
read from GitLab at the merge commit ([`manual.py`](src/docbot/drafting/manual.py#L56)).
DocBot cannot create pages and does not update translations.

`llm/` holds the provider seam and the tool loop, and knows nothing about manuals.
[`mistral.py`](src/docbot/llm/mistral.py) is the only module that imports `mistralai`.
`drafting/` holds what DocBot asks the model, and the tools and checks it needs.
Imports point one way: the top level uses `drafting/`, and `drafting/` uses `llm/`.

## Triage

[`triage()`](src/docbot/drafting/triage.py#L48): one conversation with one tool.

**In.** [`update.py:66`](src/docbot/update.py#L66) hands triage four things: the
merge request, the diffs that were not ignored, the manual, and the pages the merge
request edited. [`_task()`](src/docbot/drafting/triage.py#L71) writes them into one
user message:

| Input | Written into the task at | Comes from |
|---|---|---|
| Merge request title, with its `!iid` | [`change.py:6`](src/docbot/drafting/change.py#L6), `mr['title']` | GitLab `GET /repository/commits/:sha/merge_requests` ([`gitlab.py:54`](src/docbot/gitlab.py#L54)), via [`update.py:33`](src/docbot/update.py#L33) |
| Merge request description | [`change.py:6`](src/docbot/drafting/change.py#L6), `mr.get("description")` | the same |
| Diff of each file that is not ignored, with its path | [`change.py:11`](src/docbot/drafting/change.py#L11) | GitLab `GET /merge_requests/:iid/diffs` ([`gitlab.py:61`](src/docbot/gitlab.py#L61)), filtered at [`update.py:57`](src/docbot/update.py#L57) |
| Page names, in manual order | [`manual.py:86`](src/docbot/drafting/manual.py#L86) | `htmlDocPages` in `gruntfile.js`. The pages are read from GitLab at [`update.py:62`](src/docbot/update.py#L62) |
| Headings of each page | [`manual.py:87`](src/docbot/drafting/manual.py#L87) | the same pages |
| The marker "already edited in this merge request" | [`manual.py:86`](src/docbot/drafting/manual.py#L86) | manual pages in the diff ([`ignore.py:39`](src/docbot/drafting/ignore.py#L39)) |

[`triage.py:72`](src/docbot/drafting/triage.py#L72) puts the merge request and the
diffs into the task, and [`triage.py:74`](src/docbot/drafting/triage.py#L74) adds the
table of contents.

**Sent.** [`triage.py:51`](src/docbot/drafting/triage.py#L51) builds the system prompt
and the task. [`triage.py:52`](src/docbot/drafting/triage.py#L52) opens the
conversation with them and one tool, `submit_triage`.
[`mistral.py:53`](src/docbot/llm/mistral.py#L53) makes the two texts the first two
messages, and [`mistral.py:57`](src/docbot/llm/mistral.py#L57) sends them, with the
tool, on every turn. That is all the model gets: triage reads no page and searches no
code.

**Checked.** Each run stores the exact system prompt and task in `result.json`
([`triage.py:59`](src/docbot/drafting/triage.py#L59)).
[`test_a_valid_answer_comes_back`](tests/test_triage.py#L20) checks two things:
- the stored texts are the ones the model was given
- the task holds the merge request's title and description, the diff, the headings
  and the edited-page marker

**Out** ([`submit_triage`](src/docbot/drafting/triage.py#L37)):

- `decision`: `doc-impact` or `no-doc-impact`
- `reason`: one or two sentences on what the change does for a user. This becomes
  "Why the manual changes" in the docs merge request.

Triage does not choose pages. That is drafting's job.

## Drafting

[`propose()`](src/docbot/drafting/proposal.py#L80): one conversation, with at most
[20 tool calls](src/docbot/llm/agent.py#L14).

**In** ([system prompt](src/docbot/drafting/proposal.py#L26), [task](src/docbot/drafting/proposal.py#L159)):
the same merge request, diff and table of contents as triage, plus these tools:

- `read_page` and `search_manual`, over the manual ([`manual.py`](src/docbot/drafting/manual.py#L34))
- `list_files`, `grep` and `read_file`, over the code at the merge commit
  ([`repo.py`](src/docbot/drafting/repo.py#L20)), unless `--diff-only` is set

**Out** ([`submit_proposal`](src/docbot/drafting/proposal.py#L59)):

- `pages`: one entry for each page the model edits, hands to a human, or read and left alone
  - `page` and `reason`
  - `decision`: `edit`, `no-change` or `needs-human`
  - `edits`: `find`/`replace` pairs, only with `edit`
- `uncertainties`: anything the model is unsure of. Examples: a screenshot that may be
  out of date, or a page the manual lacks.

A proposal is accepted only if it [validates](src/docbot/drafting/proposal.py#L118):
- every page exists and is answered once
- every `find` matches exactly once
- at most 5 pages are edited

If it does not validate, the error goes back to the model, which tries again within
the same call budget.
[`edits.apply()`](src/docbot/drafting/edits.py#L36) tolerates whitespace differences
in `find`, and re-wraps the new lines to the page's own line width.

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
| `needs-human` | A conversation ended without a valid answer, or no page was edited and one needs a human | — |
| `dry-run` | `--dry-run` | —, the diff is in `diff` |
| `opened` | At least one page was edited | Opened |
| `error` | GitLab or the provider was unreachable or refused, or `doc-map.json` or `gruntfile.js` is missing | — |

Exit codes:
- 0: done, including "nothing to do" and `needs-human`
- 1: `error`
- 2: a usage or configuration error, raised before any network call

## Model, performance and cost

**Model:** `mistral-medium-3-5` (`DOCBOT_LLM_MODEL`), theoretically capable of reasoning. Prices as of
2026-09-30, per million tokens:
- input: $1.5
- cached input: $0.15
- output: $7.5

The API keeps no state, so every turn resends the whole conversation. Cost grows with
the number of turns, times the size of the diff, the table of contents and the tool
results. DocBot requests prompt caching, but a hit is not guaranteed. One call took
over 120 s, so the timeout is 300 s. Responses 429 and 5xx are retried for up to
5 minutes ([`mistral.py`](src/docbot/llm/mistral.py#L30)).

**Measured on 2026-10-01**, with triage and drafting split as they are now, but before
repo mode became the default on 2026-10-07:

- **Demo fixture**: the 5 scenarios in `devinfra/scenarios` at the time, plus the
  comment kinds of `open-test-mr.sh`, in both modes.
  - Every outcome was as expected.
  - $0.16 for 15 runs, about $0.01 per merge.
- **Zulip replay**: 15 commits from zulip/zulip, against a 464-page help centre, in
  diff mode.
  - Triage was right 15 times out of 15: 9 changes with doc impact and 6 refactors.
  - Page choice: 6 of the 9 existing pages the authors edited. This leaves out one
    case, which the model answered `needs-human` for the right area. It also edited
    2 pages the authors did not.
  - Drafts: 2 the same as the author's, 2 close, 3 partial, 1 misleading, and 1 page
    with invented labels.
  - Cost: $1.37 in all. That is $0.024 per refactor and about $0.14 per change with
    doc impact, at most $0.40 (14 changed files).
  - Finding the page works. What the draft says is the weak part.

**Why Medium and not Large 3** (`mistral-large-2512`). Large is about 6 times cheaper
per draft, but fails on the harder calls:

| | Large 3 | Medium 3.5 |
|---|---|---|
| Triage: a feature that a flag turns on (`account-expiry`) | 1 of 30 | 23 of 24 |
| Draft: the kiosk exit-passcode step | 0 of 30 | 19 of 19 |
| Cost per diff-mode draft | about $0.0005 | about $0.003 |

**Not measured yet:**

- Repo mode since the redesign. In the first design it cost 3 to 4 times as much as
  diff mode.
- Zulip in repo mode, and the scenarios added on 2026-10-07.

**Known limit:** triage has no repo tools. A change whose effect only the code shows
can therefore stop at triage.

The figures come from `docs/docbot-mistral-prototype.md` in the MobiManual
repository, in "Progress" and "Decisions of 2026-10-01". DocBot does not compute cost
itself. The token counts are in `result.json`.

## Running

Settings come from the environment ([`config.py`](src/docbot/config.py)):

| Variable | Example |
|---|---|
| `DOCBOT_GITLAB_URL` | `http://gitlab.orb.local` |
| `DOCBOT_PROJECT` | `root/mobivisor-console` |
| `DOCBOT_GITLAB_TOKEN` | A token with `api` scope |
| `MISTRAL_API_KEY` | The model provider's key |
| `DOCBOT_LLM_MODEL` | `mistral-medium-3-5` |

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
