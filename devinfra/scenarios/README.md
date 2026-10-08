# Scenarios

Real changes to the fixture, each one a merge request DocBot's model has to
judge. `scripts/open-test-mr.sh <name>` applies one to `main` with `git am` and
opens a merge request with the patch's own title and description.

**Worth documenting:**

| Scenario | Change | What it tests |
|---|---|---|
| `ios-department` | The iOS enrollment wizard asks for the device's department | Adding a step to the right page |
| `kiosk-passcode` | Kiosk policies get their own exit passcode | Correcting a sentence the change makes wrong, not only adding one, when two other pages also talk about the device passcode |
| `devices-filter` | The device list gets a compliance filter | Editing one page when four mention compliance |
| `account-expiry` | A feature flag turns on an optional expiry date in the Add user form | Writing from code the diff does not show: the diff is the flag. Needs repo mode |
| `command-expiry` | Queued commands expire after 72 hours instead of 24 | A one-line server change that makes two pages wrong; finding both |
| `retire-label` | **Retire** is renamed **Unenroll**, and the author updates one page themselves | A label rename in `en.json` alone; finding the pages the author missed, and leaving theirs alone |
| `passcode-history` | Passcode policies can forbid reusing recent passcodes | Choosing the passcode policy page among the many that mention passcodes or passwords, and editing a table |
| `invite-link-72h` | A new account's password link lasts 72 hours; a reset link stays at 48 | Changing one of two "48 hours" on the same page, the one the change is about |
| `helpdesk-update-os` | Helpdesk may send **Update OS** | A one-line permission change that makes two tables wrong, on two pages |
| `wipe-confirm-name` | A wipe is confirmed with the device's name instead of the password | Correcting a sentence from a changed label and a changed setting |
| `auditlog-export-removed` | **Export CSV** is removed from the Audit Log | A removal: deleting a sentence, and correcting another one that now asks for what is gone |
| `settings-branding` | Settings gets a Branding section for a company logo | New functionality that fits an existing page: adding a section |
| `wifi-policy` | A fourth policy type, Wi-Fi, with its own console page | New functionality that needs a page the manual lacks, and also makes a sentence wrong: correcting the sentence and naming the missing page |
| `locations-page` | A new Locations page shows where devices are | New functionality that needs a page the manual lacks and changes no existing page: handing it to a human instead of editing stand-ins |

**Not worth documenting:**

| Scenario | Change | What it tests |
|---|---|---|
| `refactor` | The users controller is split into helpers, with nothing visible changing | Silence on a refactor |
| `apns-retry` | Apple Push sends are retried when Apple throttles them | Silence when a page's name matches the code: `_apns.md` is about Access Point Names |
| `lost-mode-dark` | A Lost mode command is merged behind a flag that stays off | Silence on a feature nobody can see yet; the counterpart of `account-expiry` |
| `dashboard-count-fix` | The dashboard stops counting retired devices | Silence on a fix that makes the product match what the manual already says |
| `retire-identifiers` | The retire command is called unenroll in the code; the label stays **Retire** | Silence on a rename inside the code; the counterpart of `retire-label` |
| `auditlog-to-date-fix` | The Audit Log's **To** date includes the whole day | Silence on a fix where the manual says nothing either way, unlike `dashboard-count-fix` |
| `tr-label-fix` | Two Turkish labels are corrected | Silence on a change to another language's labels |
| `a11y-labels` | Unlabelled controls get an `aria-label` | Silence on a template and `en.json` change that only screen readers notice |
| `ring-duration-documented` | **Ring** lasts 1 minute instead of 2, and the author updates the only page that says so | Silence when the author did it all; the counterpart of `retire-label` |
| `drop-account-expiry` | The unreleased account expiry feature is removed | Silence on removing something that was never switched on |

What DocBot should do is stated in each patch, below its `---`:

```
Expected: worth documenting. Triage answers doc-impact. The draft changes ...
Expected-outcome: opened
Expected-edits: _devices_id.md _devicescommands.md
Expected-may-edit: chapter1.md
Expected-outcome-diff-only: needs-human
```

`Expected:` describes the right result in words, for a person to judge the
draft by. The other lines are what the tools check: update-manual's outcome,
the pages that must be edited, the pages that may be edited as well, and, where
`--diff-only` cannot write the edit, the outcome then (with no page edited).
`git am` leaves everything between `---` and the diff out of the commit message,
so the expectation never reaches the merge request description the model reads.

`open-test-mr.sh --merge` prints the expectation next to what DocBot did: the
outcome, triage's reason, each page's decision and reason, a check of the pages
against `Expected-edits`, and the manual diff. It keeps each `result.json` in
`.runtime/mr-results/`.

`tests/live/test_live_update.py` in `demo-repo/tools/docbot/` runs every
scenario through `update-manual` without the stack, in repo mode and with
`--diff-only`, and writes each result to `.runtime/docbot-results/`, to compare
against the `Expected:` line. `tests/live/test_live_mistral.py` runs drafting
alone on the scenarios worth documenting and checks that each page the
`Expected:` line requires comes back edited.

## Adding one

Make the change as a commit in a clone of the fixture, with a title and a
description written the way a developer would write them. Do not mention the
manual. Then:

```bash
git format-patch -1 --stdout --zero-commit --no-signature > scenarios/<name>.patch
```

Add the `Expected:` lines directly below the patch's `---` line. `Expected:`
should start with "worth documenting" or "not worth documenting": that is what
`open-test-mr.sh --help` lists. `Expected-outcome:` is required; the other
lines only where they apply. The live tests and `open-test-mr.sh` read them
from the patch, so nothing else needs changing.

`demo-repo/README.md` lists the facts the manual states on several pages and
the words it uses for different things: a scenario built on one of them tests
more than one built on a single sentence.

A scenario applies once. After it has merged, `main` already has it, and the
script says so. Re-seed with `./scripts/seed-project.sh` to run it again. A
change to the fixture can break a patch's context; check that every patch still
applies to a fresh copy of the fixture after changing it.
