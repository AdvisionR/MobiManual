# Scenarios

Real changes to the fixture, each one a merge request DocBot's model has to
judge. `scripts/open-test-mr.sh <name>` applies one to `main` with `git am` and
opens a merge request with the patch's own title and description.

| Scenario | Change | Worth documenting? |
|---|---|---|
| `ios-department` | The iOS enrollment wizard asks for the device's department | Yes |
| `kiosk-passcode` | Kiosk policies get their own exit passcode | Yes. It makes an existing sentence on the page wrong |
| `devices-filter` | The device list gets a compliance filter | Yes, on one of the area's two pages |
| `refactor` | The users controller is split into helpers, with nothing visible changing | No |

The expected outcome in detail is in each patch, on the `Expected:` line below
its `---`. `git am` leaves everything between `---` and the diff out of the
commit message, so the expectation never reaches the merge request description
the model reads.

Until DocBot's drafting step lands, every merged scenario still produces the
placeholder docs merge request. The expectations describe the model-drafting
step planned in `docs/docbot-llm-draft.md`.

## Adding one

Make the change as a commit in a clone of the fixture, with a title and a
description written the way a developer would write them. Do not mention the
manual. Then:

```bash
git format-patch -1 --stdout --zero-commit --no-signature > scenarios/<name>.patch
```

Add one `Expected: …` line directly below the patch's `---` line. It should
start with "worth documenting" or "not worth documenting": that is what
`open-test-mr.sh --help` lists.

A scenario applies once. After it has merged, `main` already has it, and the
script says so. Re-seed with `./scripts/seed-project.sh` to run it again.
