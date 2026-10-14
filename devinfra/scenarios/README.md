# Scenarios

Real changes to the fixture, each one a merge request DocBot's model has to
judge. `scripts/open-test-mr.sh <name>` applies one to `main` with `git am` and
opens a merge request with the patch's own title and description.

Each scenario lives in a folder named after the kind of change it covers, as
`<folder>/<name>.patch`. A folder holds both the scenarios that need a manual
edit and their counterparts that need silence. Names are unique across folders,
so the name alone selects a scenario. Each heading below names a group by its
title and its folder. [docs/docbot-scenarios.md](../../docs/docbot-scenarios.md)
uses the same titles, and says why these groups and which scenarios are planned
for each.

"Expected" is the patch's `Expected-outcome`: **edit** opens a docs merge
request, **silent** is `no-doc-impact`, **needs-human** edits nothing and hands the
change to a person.

### Time limits and expiry (`time-limits/`)

| Scenario | Expected | Change | What it tests |
|---|---|---|---|
| `command-expiry` | edit | Queued commands expire after 72 hours instead of 24 | A one-line server change that makes two pages wrong; finding both |
| `invite-link-72h` | edit | A new account's password link lasts 72 hours; a reset link stays at 48 | Changing one of two "48 hours" on the same page, the one the change is about |

### Roles and permissions (`roles-and-permissions/`)

| Scenario | Expected | Change | What it tests |
|---|---|---|---|
| `helpdesk-update-os` | edit | Helpdesk may send **Update OS** | A one-line permission change that makes two tables wrong, on two pages |

### Other rules that change (`rule-changes/`)

| Scenario | Expected | Change | What it tests |
|---|---|---|---|
| `wipe-confirm-name` | edit | A wipe is confirmed with the device's name instead of the password | Correcting a sentence from a changed label and a changed setting |

### New functionality on an existing page (`new-on-existing-page/`)

| Scenario | Expected | Change | What it tests |
|---|---|---|---|
| `devices-filter` | edit | The device list gets a compliance filter | Editing one page when four mention compliance |
| `passcode-history` | edit | Passcode policies can forbid reusing recent passcodes | Choosing the passcode policy page among the many that mention passcodes or passwords, and editing a table |
| `ios-department` | edit | The iOS enrollment wizard asks for the device's department | Adding a step to the right page |
| `kiosk-passcode` | edit | Kiosk policies get their own exit passcode | Correcting a sentence the change makes wrong, not only adding one, when two other pages also talk about the device passcode |
| `settings-branding` | edit | Settings gets a Branding section for a company logo | New functionality that fits an existing page: adding a section |

### New functionality that needs a new page (`new-page-needed/`)

| Scenario | Expected | Change | What it tests |
|---|---|---|---|
| `wifi-policy` | edit | A fourth policy type, Wi-Fi, with its own console page | New functionality that needs a page the manual lacks, and also makes a sentence wrong: correcting the sentence and naming the missing page |
| `locations-page` | needs-human | A new Locations page shows where devices are | New functionality that needs a page the manual lacks and changes no existing page: handing it to a human instead of editing stand-ins |

### Feature flags (`feature-flags/`)

| Scenario | Expected | Change | What it tests |
|---|---|---|---|
| `account-expiry` | edit | A feature flag turns on an optional expiry date in the Add user form | Writing from code the diff does not show: the diff is the flag. Needs repo mode |
| `lost-mode-dark` | silent | A Lost mode command is merged behind a flag that stays off | Silence on a feature nobody can see yet; the counterpart of `account-expiry` |
| `drop-account-expiry` | silent | The unreleased account expiry feature is removed | Silence on removing something that was never switched on |

### Removals (`removals/`)

| Scenario | Expected | Change | What it tests |
|---|---|---|---|
| `auditlog-export-removed` | edit | **Export CSV** is removed from the Audit Log | A removal: deleting a sentence, and correcting another one that now asks for what is gone |

### Renames (`renames/`)

| Scenario | Expected | Change | What it tests |
|---|---|---|---|
| `retire-label` | edit | **Retire** is renamed **Unenroll**, and the author updates one page themselves | A label rename in `en.json` alone; finding the pages the author missed, and leaving theirs alone |
| `retire-identifiers` | silent | The retire command is called unenroll in the code; the label stays **Retire** | Silence on a rename inside the code; the counterpart of `retire-label` |

### Bug fixes (`bug-fixes/`)

| Scenario | Expected | Change | What it tests |
|---|---|---|---|
| `dashboard-count-fix` | silent | The dashboard stops counting retired devices | Silence on a fix that makes the product match what the manual already says |
| `auditlog-to-date-fix` | silent | The Audit Log's **To** date includes the whole day | Silence on a fix where the manual says nothing either way, unlike `dashboard-count-fix` |

### Languages (`languages/`)

| Scenario | Expected | Change | What it tests |
|---|---|---|---|
| `tr-label-fix` | silent | Two Turkish labels are corrected | Silence on a change to another language's labels |

### More than one change in a merge request (`mixed-merge-requests/`)

| Scenario | Expected | Change | What it tests |
|---|---|---|---|
| `ring-duration-documented` | silent | **Ring** lasts 1 minute instead of 2, and the author updates the only page that says so | Silence when the author did it all; the counterpart of `retire-label` |

### Visible, but below the manual's level of detail (`below-manual-detail/`)

| Scenario | Expected | Change | What it tests |
|---|---|---|---|
| `a11y-labels` | silent | Unlabelled controls get an `aria-label` | Silence on a template and `en.json` change that only screen readers notice |

### Nothing a console user sees (`invisible-changes/`)

| Scenario | Expected | Change | What it tests |
|---|---|---|---|
| `refactor` | silent | The users controller is split into helpers, with nothing visible changing | Silence on a refactor |
| `apns-retry` | silent | Apple Push sends are retried when Apple throttles them | Silence when a page's name matches the code: `_apns.md` is about Access Point Names |

A fourteenth group, Generated pages (`generated-pages/`), has no scenario yet. Git keeps no empty
folders, so it appears with its first patch.

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
git format-patch -1 --stdout --zero-commit --no-signature > scenarios/<folder>/<name>.patch
```

Put it in the folder for the kind of change it covers, and give it a name no
other folder uses: the live tests and `open-test-mr.sh` refuse a name that is in
two folders. A new kind of change gets a new folder, and a section above.

Add the `Expected:` lines directly below the patch's `---` line. `Expected:`
should start with "worth documenting" or "not worth documenting": that is what
`open-test-mr.sh --help` lists. `Expected-outcome:` is required; the other
lines only where they apply. The live tests and `open-test-mr.sh` find the
patch in its folder and read them from it, so nothing else needs changing.

`demo-repo/README.md` lists the facts the manual states on several pages and
the words it uses for different things: a scenario built on one of them tests
more than one built on a single sentence.

A scenario applies once. After it has merged, `main` already has it, and the
script says so. Re-seed with `./scripts/seed-project.sh` to run it again. A
change to the fixture can break a patch's context; check that every patch still
applies to a fresh copy of the fixture after changing it.
