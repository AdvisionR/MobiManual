# DocBot

Keeps the user manual in step with what merges to `main`. Jenkins runs it after
every merge, in the `DocBot` stage of the `Jenkinsfile`.

For now the drafting step is a placeholder. For each merged merge request, DocBot
opens a docs merge request from branch `docbot/mr-<iid>`, labelled
`docbot-generated`, that appends the merge request's diff to
`public/doc/en/docbot-changes.md`. The drafting agent will replace
`src/docbot/draft.py`. Everything around it is the real wiring: resolving the
merge, reading the manual at the merge commit, committing through the API, and
opening the merge request.

## Running it

Settings come from the environment. If one is missing, DocBot exits with code 2
before making any network call.

| Variable | Example |
|---|---|
| `DOCBOT_GITLAB_URL` | `http://gitlab.orb.local` |
| `DOCBOT_PROJECT` | `root/mobivisor-console` |
| `DOCBOT_GITLAB_TOKEN` | A token with `api` scope |

On a laptop, with [uv](https://docs.astral.sh/uv/):

```bash
cd tools/docbot
uv run docbot update-manual --sha <merge commit> --dry-run   # prints the manual diff, writes nothing
uv run pytest
```

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
