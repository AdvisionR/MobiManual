# DocBot

Keeps the user manual in step with what merges to `main`. Jenkins runs it after
every merge, in the `DocBot` stage of the `Jenkinsfile`.

For each merged merge request, DocBot:

1. Drops the changed files `doc-map.json` ignores. If nothing is left, it stops.
2. Asks a model whether the change makes the manual wrong or incomplete at all
   (triage). It reads the diff next to the table of contents built from
   `htmlDocPages` in `gruntfile.js`, and answers yes or no, with a reason.
3. If it does, asks the model to find the English pages the change affects and
   propose find-and-replace edits to them (drafting). The model reads and
   searches the manual itself, with `read_page` and `search_manual`, and decides
   which pages to change.
4. Commits the edited pages on branch `docbot/mr-<iid>` and opens a docs merge
   request labelled `docbot-generated`, with the model's reasons in its
   description.

When triage finds nothing, or drafting changes nothing, no merge request opens.
The outcome is recorded in the result only: `no-doc-impact`, `no-change` or
`needs-human`.

## Layout

```
src/docbot/
├── cli.py              the command line: arguments, output, exit codes
├── config.py           settings; the only module that reads the environment
├── update.py           update-manual: one merge in, one docs merge request out
├── gitlab.py           the GitLab API; the only module that sends requests with httpx2
├── resolve.py          which merge request produced a commit
├── llm/                talking to a model with tools; knows nothing about manuals
│   ├── __init__.py     the seam between DocBot and a provider
│   ├── agent.py        the tool loop
│   └── mistral.py      the only module that imports mistralai
└── drafting/           what DocBot asks the model, and the tools and checks it needs
    ├── ignore.py       the doc map's ignore list: which changed files the model sees
    ├── manual.py       the table of contents, and read_page and search_manual over the pages
    ├── change.py       the merge request and its diff, as the model reads them
    ├── triage.py       the triage conversation: doc impact or not
    ├── proposal.py     the drafting conversation: which pages, and the edits
    ├── repo.py         read-only git tools for the model to search with
    └── edits.py        find-and-replace edits on manual pages
```

Imports point one way: the top level uses `drafting/` and `llm/`, `drafting/`
uses `llm/`, and `llm/` uses neither. The tests in `tests/` are one file per
module, plus `fakes.py`, a scripted model. `tests/live/` holds the ones that call a real model.

## Running it

Settings come from the environment. If one is missing, DocBot exits with code 2
before making any network call.

| Variable | Example |
|---|---|
| `DOCBOT_GITLAB_URL` | `http://gitlab.orb.local` |
| `DOCBOT_PROJECT` | `root/mobivisor-console` |
| `DOCBOT_GITLAB_TOKEN` | A token with `api` scope |
| `MISTRAL_API_KEY` | The model provider's key, read by triage and drafting |
| `DOCBOT_LLM_MODEL` | `mistral-medium-3-5` |

On a laptop, with [uv](https://docs.astral.sh/uv/), the settings live in `.env`.
That file is gitignored. `.env.example` documents it:

```bash
cd tools/docbot
cp .env.example .env                  # once, then fill in the token and the key
uv run --env-file .env docbot update-manual --sha <merge commit> --dry-run   # prints the manual diff, writes nothing
uv run pytest
```

Variables already exported in the shell take precedence over `.env`.

`--context repo --repo <checkout>` also lets the drafting model search the code
at the merge commit (`list_files`, `grep`, `read_file`). The checkout must
contain that commit. The default, `--context diff`, gives it the diff and the
manual only.

`uv run pytest` needs neither GitLab nor a key. The tests marked `live`, in
`tests/live/`, call Mistral with the fixture and each scenario from `devinfra/scenarios`, and cost
credits, so they only run when asked for:

```bash
uv run --env-file .env pytest -m live -s -k update   # update-manual end to end, GitLab replayed from git
uv run --env-file .env pytest -m live -s -k mistral  # drafting only, on the pages each scenario expects
```

`-k update` is the laptop dry run without the stack. Each scenario, and each
comment kind of `open-test-mr.sh`, runs through `update-manual`, and the result
goes to `devinfra/.runtime/docbot-results/` in the MobiManual repository.

`-k zulip` selects the replay of zulip/zulip's history instead, set up in the
MobiManual repository's `devinfra/` (`scripts/fetch-zulip.sh`, `zulip/cases.json`).
It is skipped where that is not available.

In CI, the Jenkinsfile creates a venv at `tools/docbot/.venv`, installs
`requirements.txt` with hash checking, and runs
`python -m docbot update-manual > result.json`. The model key comes from the
`docbot-llm-key` Jenkins credential, bound to `MISTRAL_API_KEY`, and the model
from `DOCBOT_LLM_MODEL` in the Jenkinsfile's `environment`.

stdout carries exactly one JSON document (`docbot.update/2`), and stderr carries
the narration. The document holds the outcome and, where the model was asked,
a `triage` and a `draft` section with every turn, tool call and token count.
The exit codes are:

- 0: done, including "nothing to do" and "needs a human"
- 1: GitLab or the model provider unreachable or refusing, or `doc-map.json`
  or `gruntfile.js` missing at the merge commit
- 2: a usage or configuration error

## Dependencies

`pyproject.toml` declares the dependencies, and `uv.lock` pins them.
`requirements.txt` is exported from the lock for CI, which has no uv. After
changing a dependency, run:

```bash
uv lock && uv export --frozen --no-dev --no-emit-project --format requirements-txt -o requirements.txt
```

## Keeping this directory movable

This directory may later move out of the repository it serves, together with
its pipeline. The MobiManual repository's `docbot-code-location.md` explains
when and why. Four rules keep that move a copy:

1. Nothing outside `tools/docbot/` is imported or executed.
2. Configuration comes only from `DOCBOT_*` variables and flags, never from
   Jenkins' own variables.
3. The only thing read implicitly from the working directory is
   `git rev-parse HEAD`, and `--sha` replaces it.
4. One JSON document goes to stdout. Narration goes to stderr.
