# DocBot

Keeps the user manual in step with what merges to `main`. Jenkins runs it after
every merge, in the `DocBot` stage of the `Jenkinsfile`.

For now the drafting step is a placeholder. For each merged merge request, DocBot
opens a docs merge request from branch `docbot/mr-<iid>`, labelled
`docbot-generated`, that appends the merge request's diff to
`public/doc/en/docbot-changes.md`. The drafting agent will replace
`src/docbot/drafting/placeholder.py`. Everything around it is the real wiring:
resolving the merge, reading the manual at the merge commit, committing through
the API, and opening the merge request.

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
    ├── proposal.py     the drafting conversation
    ├── repo.py         read-only git tools for the model to search with
    ├── edits.py        find-and-replace edits on manual pages
    └── placeholder.py  today's drafting step, until update-manual uses proposal.py
```

Imports point one way: the top level uses `drafting/` and `llm/`, `drafting/`
uses `llm/`, and `llm/` uses neither. The tests in `tests/` are one file per
module. `tests/live/` holds the ones that call a real model.

## Running it

Settings come from the environment. If one is missing, DocBot exits with code 2
before making any network call.

| Variable | Example |
|---|---|
| `DOCBOT_GITLAB_URL` | `http://gitlab.orb.local` |
| `DOCBOT_PROJECT` | `root/mobivisor-console` |
| `DOCBOT_GITLAB_TOKEN` | A token with `api` scope |
| `MISTRAL_API_KEY` | The model provider's key, read by the drafting step |
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

`uv run pytest` needs neither GitLab nor a key. The tests marked `live`, in
`tests/live/`, call Mistral with the fixture and each scenario from `devinfra/scenarios`, and cost
credits, so they only run when asked for:

```bash
uv run --env-file .env pytest -m live -s   # prints each proposal, every turn included
```

`-k zulip` selects the replay of zulip/zulip's history instead, set up in the
MobiManual repository's `devinfra/` (`scripts/fetch-zulip.sh`, `zulip/cases.json`).
It is skipped where that is not available.

In CI, the Jenkinsfile creates a venv at `tools/docbot/.venv`, installs
`requirements.txt` with hash checking, and runs
`python -m docbot update-manual > result.json`.

stdout carries exactly one JSON document (`docbot.update/1`), and stderr carries
the narration. The exit codes are:

- 0: done, including "nothing to do"
- 1: GitLab unreachable, or refusing the request
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
