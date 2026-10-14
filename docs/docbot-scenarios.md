# DocBot — test scenarios, grouped by kind of change

**Status:** catalogue, 2026-10-13; updated 2026-10-14. 30 scenarios are built in
`devinfra/scenarios/`: the first 24, and six added on 2026-10-14 for merge requests that
are messy or have no description (see "Added on 2026-10-14"). The 17 marked **new** are
proposed here and not built yet.
**Relationship to other documents:** groups the scenarios of
[the scenarios README](../devinfra/scenarios/README.md), which says how to run and add
them. Results per scenario are in [docbot-repo-mode-scenarios.md](docbot-repo-mode-scenarios.md).
Tags as in the foundation doc: **[DECIDED]**, **[EVIDENCE]**, **[PROPOSED]**,
**[UNKNOWN]**.

---

## Short answer

- **14 groups, by the kind of change a developer makes [PROPOSED].** Each group puts the
  scenarios that need a manual edit next to their silent counterparts, so it shows both
  what DocBot has to find and what it has to leave alone.
- **17 new scenarios [PROPOSED]**: 12 that need an edit and 5 that need silence. They
  cover what the 24 leave out. That includes a new automatic rule with no UI (accounts
  disabled after 180 days without a sign-in) and a new role next to Administrator,
  Helpdesk and Auditor. It also includes a bug fix the manual had documented as a
  caveat, a fixed value that becomes a setting, a rename whose old word means something
  else on another page, a generated page, a new console language, a visible change
  hidden in a refactor, and harder negatives.
- **The built negatives no longer tell a better DocBot from a worse one [EVIDENCE].** All 10 were
  silent in both repo-mode runs on 2026-10-13. Each new negative looks visible: a nightly
  job in the module behind "48 hours", a security fix about passwords, a sort order, the
  wording of the sign-in messages, a dependency upgrade.
- **One expectation is a decision, not a fact [UNKNOWN]:** what DocBot should do with a
  stale generated table (`restriction-schema-only`). I propose a hand-written row
  identical to what the generator renders.

## How to read the groups

Each scenario is in one group: the one that says most about what DocBot has to do.
Each group is a folder in `devinfra/scenarios/`, named in its heading, and its
patches live there. "Expected" is the patch's `Expected-outcome` and `Expected-edits`. **edits** lists the
pages that must change. **silent** means `no-doc-impact`. **needs-human** means no page
is edited and a person has to write one.

For each new scenario there is a short spec to build the patch from: the change, the
developer's title, the expectation in words (it becomes the `Expected:` line) and the
lines the tools check.

### Why group by kind of change

| Grouping | Verdict | Why |
|---|---|---|
| By kind of change: a time limit, a role, a rename, a fix … | **Chosen** | It is how a developer describes a merge request, and it decides the edit DocBot has to make: correct a number, add a row, avoid a homonym. Counterparts end up in the same group |
| Worth or not worth documenting, the README's split | Rejected as the main split | It separates each scenario from its counterpart: `retire-label` and `retire-identifiers` end up in different tables |
| By manual page | Rejected | Most scenarios touch two pages or more, and the page says nothing about how hard the change is |
| By DocBot failure mode: miss, over-edit, invent, stand-in | Rejected as the main split | A scenario usually probes several. They are named in "What it tests" instead |

## Overview

| Group | Built: change / silent | New: change / silent |
|---|---|---|
| Time limits and expiry (`time-limits/`) | 2 / 0 | 2 / 1 |
| Roles and permissions (`roles-and-permissions/`) | 1 / 0 | 1 / 0 |
| Other rules that change (`rule-changes/`) | 1 / 0 | 3 / 0 |
| New functionality on an existing page (`new-on-existing-page/`) | 5 / 0 | — |
| New functionality that needs a new page (`new-page-needed/`) | 2 / 0 | — |
| Feature flags (`feature-flags/`) | 1 / 2 | — |
| Removals (`removals/`) | 1 / 0 | 1 / 0 |
| Reverts (`reverts/`) | 1 / 0 | — |
| Renames (`renames/`) | 1 / 1 | 1 / 0 |
| Bug fixes (`bug-fixes/`) | 0 / 2 | 1 / 0 |
| Languages (`languages/`) | 0 / 1 | 1 / 0 |
| More than one change in a merge request (`mixed-merge-requests/`) | 2 / 1 | 1 / 0 |
| No description (`no-description/`) | 2 / 1 | — |
| Generated pages (`generated-pages/`) | — | 1 / 0 |
| Visible, but below the manual's level of detail (`below-manual-detail/`) | 0 / 1 | 0 / 2 |
| Nothing a console user sees (`invisible-changes/`) | 0 / 2 | 0 / 2 |
| **Total** | **19 / 11** | **12 / 5** |

---

## Time limits and expiry (`time-limits/`)

Durations, deadlines, and rules that act on their own once time has passed. The manual
states several (48 hours, 24 hours, 7 days, 365 days, 30 minutes). Each comes from one
constant in `server/`, so a one-line diff can make a page wrong.

| Scenario | | Expected | What it tests |
|---|---|---|---|
| `command-expiry` | built | edits `_devices_id.md`, `_devicescommands.md` | A one-line server change that makes two pages wrong; finding both |
| `invite-link-72h` | built | edits `_users.md` | Changing one of two "48 hours" on the same page, the one the change is about |
| `inactive-accounts-disabled` | **new** | edits `_users.md`, `_settings.md` | A new rule with no UI and no sentence to correct: adding it in the right section, and extending a list of emails on another page |
| `audit-retention-setting` | **new** | edits `_auditlog.md`, `_settings.md` | A fixed number becomes a setting: correcting the number on one page, adding the field on another |
| `purge-expired-invites` | **new** | silent | Silence on a nightly job in the module that the manual's "48 hours" comes from |

### `inactive-accounts-disabled` **[PROPOSED]**

**Change.** A new `server/auth/inactivity.js` runs every night, as the audit purge does.
An account that has not signed in for 180 days (`INACTIVE_DAYS`) is disabled, exactly as
**Disable** does it, and its user gets an email 14 days before (`WARNING_DAYS`). Signing
in resets the count. The last enabled administrator is never disabled. No template or
label changes. Title: *Disable accounts that have not signed in for 180 days*.

**Expected.** Worth documenting, although the diff is one new server file. The draft adds
the rule to "Disabling a user" on `_users.md`: 180 days without a sign-in, the warning
email 14 days before, and **Enable** to let the user in again. The exception for the last
administrator may be included. The draft also adds the warning to the emails listed under
"Email notifications" on `_settings.md`. "Staying signed in" on `chapter1.md` is about
the 30-minute session timeout, which is a different inactivity, and stays unchanged. So
does the lockout after 5 failed attempts. "Six months" instead of 180 days is imprecise.

```
Expected-outcome: opened
Expected-edits: _users.md _settings.md
Expected-may-edit: chapter1.md
```

### `audit-retention-setting` **[PROPOSED]**

**Change.** `server/audit/retention.js` takes the retention from the settings instead of
a constant: **Audit log retention (days)** under **Settings > Security**, from 90 to
3650, default 365. `settings.html` gets the field, and the locale files get its label.
Title: *Make audit log retention configurable*.

**Expected.** Worth documenting. The draft corrects "Entries are kept for 365 days and
then deleted" under "Retention" on `_auditlog.md`: the period is set under
**Settings > Security**, and it is 365 days unless changed. It adds the field, its range
and its default to "Security" on `_settings.md`. "Export the entries you need to keep
longer" stays true. Either edit without the other is incomplete.

```
Expected-outcome: opened
Expected-edits: _auditlog.md _settings.md
```

### `purge-expired-invites` **[PROPOSED]**

**Change.** `server/auth/invitation.js` gets a nightly `purgeExpired`, which deletes
password links 30 days after they expired. An unknown link gets the same "link expired"
answer as an expired one, so nothing a user sees changes. Title: *Delete expired
password links*.

**Expected.** Not worth documenting. The draft changes no page: links still last
48 hours and still work only once. It is a trap twice over. `invitation.js` is the
module behind "valid for 48 hours" on `_users.md`, and the change is a nightly job, like
`inactive-accounts-disabled`. A draft that writes "expired links are deleted after
30 days" adds a fact no reader can observe.

```
Expected-outcome: no-doc-impact
```

## Roles and permissions (`roles-and-permissions/`)

Who may do what. The Roles table on `_users.md` and the command table on
`_devicescommands.md` both come from `server/auth/permissions.js`. `chapter1.md` lists
the roles by name, and `_auditlog.md` names who may read it.

| Scenario | | Expected | What it tests |
|---|---|---|---|
| `helpdesk-update-os` | built | edits `_users.md`, `_devicescommands.md` | A one-line permission change that makes two tables wrong, on two pages |
| `enrollment-manager-role` | **new** | edits `chapter1.md`, `_users.md` | New functionality that belongs on an existing page: a row in the Roles table, plus a list of roles on another page that becomes incomplete |

### `enrollment-manager-role` **[PROPOSED]**

**Change.** `server/auth/permissions.js` gets a fourth role, `enrollment_manager`, which
may enroll Android and iOS devices and view devices and groups (`enrollment.android`,
`enrollment.ios`, `devices.read`, `groups.read`). The locale files label it **Enrollment
manager**. The Add user form takes its list of roles from the server, so no template
changes. Title: *Add an Enrollment manager role*. The description says that the staff
who set up new devices should not see policies, users or the Audit Log.

**Expected.** Worth documenting. The draft adds an **Enrollment manager** row to the
Roles table on `_users.md`, and corrects "Administrator, Helpdesk or Auditor" under
"Roles" on `chapter1.md`. Pages that name roles for other reasons stay as they are. The
role sends no command, so "Who may send it" on `_devicescommands.md` is unchanged. It
cannot read the Audit Log, so "Administrators and auditors can read it" is unchanged.
Imported accounts still get the Auditor role. A sentence on the enrollment pages that
says who may enroll is acceptable, since `_settings.md` and `_auditlog.md` also say who
may use them.

```
Expected-outcome: opened
Expected-edits: chapter1.md _users.md
Expected-may-edit: _enrollment_android.md _enrollment_ios.md
```

## Other rules that change (`rule-changes/`)

A rule the manual states that is not a time limit: a minimum, a confirmation, a
restriction, where a command runs.

| Scenario | | Expected | What it tests |
|---|---|---|---|
| `wipe-confirm-name` | built | edits `_devicescommands.md` | Correcting a sentence from a changed label and a changed setting |
| `password-min-12` | **new** | edits `chapter1.md`, `_users.md` | A number on two pages, while another page has its own "Minimum length" for the device passcode; the mirror of `passcode-history` |
| `ring-ios-supervised` | **new** | edits `_devicescommands.md`, `_enrollment_ios.md` | A second page that a search for the command's name does not find: the list of what needs supervision |
| `delete-nonempty-group` | **new** | edits `_groups.md` | A restriction that is lifted: correcting it, and keeping the sentence next to it that still holds |

### `password-min-12` **[PROPOSED]**

**Change.** `MIN_LENGTH` in `server/auth/password-policy.js` goes from 8 to 12. A letter
and a digit are still required, and existing passwords keep working until they are
changed. Title: *Require 12 characters for console passwords*.

**Expected.** Worth documenting. The draft changes 8 to 12 on both pages that state it:
"Signing in" on `chapter1.md` and "Resetting a password" on `_users.md`. **Minimum
length** on `_policies_passcode.md` (4 to 16, default 6) is for the device passcode and
stays. The draft may add that existing passwords keep working.

```
Expected-outcome: opened
Expected-edits: chapter1.md _users.md
```

### `ring-ios-supervised` **[PROPOSED]**

**Change.** In `server/commands/definitions.js`, **Ring** runs on iOS too, but only on
supervised devices (`platforms: ['android', 'ios'], supervisedOnly: true`), as
**Clear passcode** does. Title: *Ring supervised iPhones*.

**Expected.** Worth documenting. The draft changes Ring's iOS cell on
`_devicescommands.md` from "no" to "supervised only". It also adds **Ring** to "Some
commands and policies need it: …" under "Supervised devices" on `_enrollment_ios.md`.
Ring's 2 minutes, and who may send it, stay unchanged.

```
Expected-outcome: opened
Expected-edits: _devicescommands.md _enrollment_ios.md
```

### `delete-nonempty-group` **[PROPOSED]**

**Change.** `groups.controller.js` offers **Delete** for every group except **Default**,
with a confirmation that says how many devices will move. A new
`server/groups/delete.js` moves the group's devices to **Default** and then deletes the
group. Title: *Delete groups that still have devices*.

**Expected.** Worth documenting. The draft corrects "Only empty groups can be deleted.
Move the devices out first." under "Deleting a group" on `_groups.md`: deleting a group
moves its devices to **Default**. It may add that they get the Default group's policies
at their next check-in. "Moving devices to another group" already says how a move works.
"The **Default** group cannot be deleted", in the same paragraph, stays. Keeping the old
rule next to a new sentence is wrong.

```
Expected-outcome: opened
Expected-edits: _groups.md
```

## New functionality on an existing page (`new-on-existing-page/`)

A new control, setting, step or section on a console page that the manual already
describes. `enrollment-manager-role`, under "Roles and permissions", is also of this
kind.

| Scenario | | Expected | What it tests |
|---|---|---|---|
| `devices-filter` | built | edits `_devices.md` | Editing one page when four mention compliance |
| `passcode-history` | built | edits `_policies_passcode.md` | Choosing the passcode policy page among the many that mention passcodes or passwords, and editing a table |
| `ios-department` | built | edits `_enrollment_ios.md` | Adding a step to the right page, and that **Finish** now waits for it |
| `kiosk-passcode` | built | edits `_policies_kiosk.md` | Correcting a sentence the change makes wrong, not only adding one, when two other pages also talk about the device passcode |
| `settings-branding` | built | edits `_settings.md` | Adding a section |

## New functionality that needs a new page (`new-page-needed/`)

| Scenario | | Expected | What it tests |
|---|---|---|---|
| `wifi-policy` | built | edits `_policies.md`, creates `_policies_wifi.md` | Correcting "three types", and creating the page the manual lacks instead of writing stand-ins |
| `locations-page` | built | creates `_locations.md` | Only a page the manual lacks: creating it instead of editing stand-ins |

Every other scenario expects no page created, so each of them also checks that DocBot
creates a page only when one is missing. None tempts it to: a change that looks like a
new screen but belongs on a page the manual has, such as a new tab on the device page,
would be the third scenario here.

## Feature flags (`feature-flags/`)

A finished feature is merged behind a flag in `public/app/features.js`, and turning the
flag on is the release.

| Scenario | | Expected | What it tests |
|---|---|---|---|
| `account-expiry` | built | edits `_users.md` | Writing from code the diff does not show: the diff is the flag |
| `lost-mode-dark` | built | silent | Silence on a feature nobody can see yet; the counterpart of `account-expiry` |
| `drop-account-expiry` | built | silent | Silence on removing something that was never switched on |

## Removals (`removals/`)

| Scenario | | Expected | What it tests |
|---|---|---|---|
| `auditlog-export-removed` | built | edits `_auditlog.md` | Deleting a sentence, and correcting another one that now asks for what is gone |
| `clear-passcode-android` | **new** | edits `_devicescommands.md`, `_policies_passcode.md` | A capability removed on one platform: advice on another page becomes wrong for that platform only, and there is nothing to replace it |

### `clear-passcode-android` **[PROPOSED]**

**Change.** `server/commands/definitions.js` removes Android from **Clear passcode**.
The agent cannot clear the passcode on current Android devices, so every such command
failed and then expired. On Android devices the command is now greyed out. Title: *Stop
offering Clear passcode on Android*.

**Expected.** Worth documenting. The draft changes Clear passcode's Android cell on
`_devicescommands.md` from "yes" to "no". It limits "If a user has forgotten the
passcode, send **Clear passcode**" on `_policies_passcode.md` to supervised iOS devices,
and does not invent what to do on Android. The supervision list on `_enrollment_ios.md`
and Helpdesk's row on `_users.md` are still true and stay unchanged.

```
Expected-outcome: opened
Expected-edits: _devicescommands.md _policies_passcode.md
```

## Reverts (`reverts/`)

A `git revert`: the title quotes the reverted commit and the description names its sha.
What the reverted commit added has to go from the manual again.

| Scenario | | Expected | What it tests |
|---|---|---|---|
| `revert-device-export` | built | edits `_devices.md` | Reading a revert as a removal; deleting the section "Exporting the list" without losing the true sentence under it, and leaving the Audit Log's own **Export CSV** alone |

## Renames (`renames/`)

| Scenario | | Expected | What it tests |
|---|---|---|---|
| `retire-label` | built | edits `_devices_id.md`, `_devicescommands.md`, `_dashboard.md`, `_users.md` | A label rename in `en.json` alone: finding the pages the author missed, including "retiring", and leaving the author's page alone |
| `retire-identifiers` | built | silent | Silence on a rename inside the code; the counterpart of `retire-label` |
| `lock-screen-label` | **new** | edits `_devicescommands.md`, `_users.md` | A rename whose old word means something else on another page. The risk is over-matching, the opposite of `retire-label` |

### `lock-screen-label` **[PROPOSED]**

**Change.** `COMMANDS.LOCK` in `en.json` goes from **Lock** to **Lock screen**, and
nothing else changes. Title: *Rename Lock to Lock screen*. The description says that
"Lock" alone does not say what gets locked.

**Expected.** Worth documenting. The draft renames the command on `_devicescommands.md`,
in the table and in the bullet, and in Helpdesk's row of the Roles table on `_users.md`.
"After 5 failed attempts the account is locked for 15 minutes" on `chapter1.md` is about
accounts and stays. So does "The user unlocks it with the device passcode".

```
Expected-outcome: opened
Expected-edits: _devicescommands.md _users.md
```

## Bug fixes (`bug-fixes/`)

A change that makes the product do what it was meant to do. Whether the manual changes
depends on what it said about the bug.

| Scenario | | Expected | What it tests |
|---|---|---|---|
| `dashboard-count-fix` | built | silent | The manual already says what the fix makes true |
| `auditlog-to-date-fix` | built | silent | The manual says nothing either way |
| `apn-seamless-switch` | **new** | edits `_apns.md` | The manual documented the bug as a caveat, so the fix makes a sentence wrong; the counterpart of the two above |

### `apn-seamless-switch` **[PROPOSED]**

**Change.** When an APN entry changes, `server/policies/apn.js` now has the device
install the new entry before it removes the old one. Before, devices removed the old
entry first and lost mobile data for a few seconds, some of them until their next
check-in. Title: *Keep mobile data up while an APN entry changes*.

**Expected.** Worth documenting. "a device can lose mobile data briefly while it
switches" on `_apns.md` describes the bug, so the draft removes it and keeps "Changing an
entry replaces it on every device in its groups". The Apple Push certificate on
`_settings.md` is the other APNs and stays.

```
Expected-outcome: opened
Expected-edits: _apns.md
```

## Languages (`languages/`)

| Scenario | | Expected | What it tests |
|---|---|---|---|
| `tr-label-fix` | built | silent | Silence on a change to another language's labels |
| `french-ui` | **new** | edits `chapter1.md` | A large diff that is almost all a new translation file, where two small changes carry the facts. Unlike `tr-label-fix`, the change does affect the English manual |

### `french-ui` **[PROPOSED]**

**Change.** The patch adds `public/i18n/fr.json` with every label (about 250 lines). It
also adds **Français** to the language menu in `index.html` and French to the list in
`i18n-static.js`. `help.js` now falls back to the English manual for a language the
manual is not written in. Title: *Add French to the console*.

**Expected.** Worth documenting. Under "Language" on `chapter1.md`, the draft adds French
to "available in English, Turkish and German". It also qualifies "the **Help** link opens
this manual in the same language": in French, it opens the English manual. Creating
`public/doc/fr/` is not DocBot's job. Naming the missing French manual in uncertainties
is fine.

```
Expected-outcome: opened
Expected-edits: chapter1.md
```

## More than one change in a merge request (`mixed-merge-requests/`)

| Scenario | | Expected | What it tests |
|---|---|---|---|
| `ring-duration-documented` | built | silent | Silence when the author already edited the only page that states the fact. `retire-label` is the case where the author did only part |
| `search-email-in-refactor` | **new** | edits `_devices.md` | One visible line inside a refactor whose title promises nothing visible |
| `commands-tab-rework` | built | edits `_devices_id.md`, `_devicescommands.md` | A 16-file feature merge request where one label matters: **Retry** for an expired command becomes **Resend**, while the app installations' **Retry** stays |
| `sprint-two-features` | built | edits `_auditlog.md`, `_appinstallations.md` | Two unrelated features in one sprint merge: documenting both, not only the first |

### `search-email-in-refactor` **[PROPOSED]**

**Change.** `server/devices/query.js` is split into one helper per filter, and a new
spec file comes with it (`doc-map.json` drops it). In the search helper, the `$or` also
matches the owner's email address. Title: *Split the device query builder into
helpers*. The description mentions the email address only in its last line, as an
aside.

**Expected.** Worth documenting, although the title promises a refactor. The draft adds
the owner's email address to "The search field matches the device name, the serial
number and the owner." on `_devices.md`. Nothing else changes.

```
Expected-outcome: opened
Expected-edits: _devices.md
```

## No description (`no-description/`)

The diff of a scenario in another group, with a ticket number as its title and no
description, as many real merge requests have. Their results next to the originals' show
how much DocBot relies on the description.

| Scenario | | Expected | What it tests |
|---|---|---|---|
| `invite-link-72h-no-description` | built | edits `_users.md` | The right one of two "48 hours", when only the code says that reset links keep theirs |
| `kiosk-passcode-no-description` | built | edits `_policies_kiosk.md` | Correcting the sentence, when only a code comment says the device passcode no longer leaves kiosk mode |
| `lost-mode-dark-no-description` | built | silent | Silence on a dark feature, when only `features.js` says it is off |

## Generated pages (`generated-pages/`)

`scripts/render-restrictions.js` renders the table on `_policies_restrictions.md` from
`schema/policies/android-restrictions.json`, and the page says "Edit the schema, not the
table." No built scenario touches that table. The `schema` kind of `open-test-mr.sh`
only appends a comment to the schema.

| Scenario | | Expected | What it tests |
|---|---|---|---|
| `restriction-schema-only` | **new** | edits `_policies_restrictions.md` | A stale generated table, on a page that says not to edit it by hand |

### `restriction-schema-only` **[PROPOSED]**

**Change.** The schema gets `location_sharing_enabled`, labelled **Allow location
sharing**, default `true`, for fully managed devices and work profiles. The author does
not run the generator, and CI does not check the table. Title: *Add a location sharing
restriction*.

**Expected.** Worth documenting. Between the markers, at the place the schema gives the
setting, the draft adds the row exactly as the generator renders it:

```
| Allow location sharing | `location_sharing_enabled` | `true` | fully-managed, work-profile |
```

The draft may say in uncertainties that `grunt render-restrictions` updates the tables
in tr and de. Any other wording or order is wrong, because
`render-restrictions.js --check` would then fail.

```
Expected-outcome: opened
Expected-edits: _policies_restrictions.md
```

**What DocBot should do here is a decision [UNKNOWN].** I propose the first row of this
table:

| Expectation | Verdict | Why |
|---|---|---|
| Opened, with the row exactly as generated | **Proposed** | The generator is deterministic and `--check` verifies the result, so a reviewer can trust a row written by hand. tr and de are translation debt, as on every other page |
| `needs-human`, saying "run the generator" | Rejected for now | It matches the page's rule. But today `needs-human` reaches nobody: it exits 0 and stays in `result.json` (evaluation, "New functionality") |
| The author ran the generator, and DocBot is silent | Rejected as a scenario | It has the same shape as `ring-duration-documented`: a page already edited in the merge request |

## Visible, but below the manual's level of detail (`below-manual-detail/`)

The user sees the change, but the manual never described the thing at that level, so
nothing it says becomes wrong. Changes like these caused the false positives in the
2026-10-08 evaluation. What counts as below the manual's level is open question 41.
The expectations here assume the manual keeps its current level of detail.

| Scenario | | Expected | What it tests |
|---|---|---|---|
| `a11y-labels` | built | silent | Template and `en.json` changes that only screen readers notice |
| `devices-default-sort` | **new** | silent | A change every user sees in the device list, at a level the manual never describes |
| `signin-messages-wording` | **new** | silent | New wording for messages the manual mentions but never quotes |

### `devices-default-sort` **[PROPOSED]**

**Change.** The device list is now sorted by last check-in, newest first, instead of in
database order (`orderBy` in `devices.html`). Title: *Show the most recently seen
devices first*.

**Expected.** Not worth documenting. `_devices.md` names the columns, the filters and
the search, and no order, so nothing it says becomes wrong. The screenshots of the list
change, and the E2E suite recaptures them. A draft that adds the sort order adds detail
the manual has nowhere else.

```
Expected-outcome: no-doc-impact
```

### `signin-messages-wording` **[PROPOSED]**

**Change.** The three messages on the sign-in page are reworded: `SIGN_IN.FAILED`,
`LOCKED` and `TIMED_OUT` in `en.json`. `LOCKED` keeps its `{{minutes}}`, and the rules
behind the messages do not change. Title: *Clearer sign-in messages*.

**Expected.** Not worth documenting. `chapter1.md` says that the sign-in page tells you
when you were signed out, but does not quote the message. The 5 attempts and
15 minutes stay the same.

```
Expected-outcome: no-doc-impact
```

## Nothing a console user sees (`invisible-changes/`)

| Scenario | | Expected | What it tests |
|---|---|---|---|
| `refactor` | built | silent | Silence on a refactor |
| `apns-retry` | built | silent | Silence when a page's name matches the code: `_apns.md` is about Access Point Names |
| `angular-translate-bump` | **new** | silent | The most common merge request there is: a dependency upgrade, with `package.json` alone |
| `log-redact-passwords` | **new** | silent | A security fix in plumbing, full of a word the manual uses on six pages |

### `angular-translate-bump` **[PROPOSED]**

**Change.** `package.json` raises `angular-translate` and
`angular-translate-loader-static-files` by a patch version. The fixture never installs
its packages, and `doc-map.json` would drop a lock file. Title: *Update
angular-translate*.

**Expected.** Not worth documenting.

```
Expected-outcome: no-doc-impact
```

### `log-redact-passwords` **[PROPOSED]**

**Change.** Before writing a line, `server/logging/logger.js` replaces the values of
`password`, `bindPassword` and `token` fields with `[redacted]`. The API had logged
request bodies at debug level, passwords included. Title: *Never write passwords or
tokens to the log*.

**Expected.** Not worth documenting. The manual says nothing about logs. "Password"
appears on `chapter1.md`, `_users.md`, `_settings.md`, `_apns.md` (the carrier's),
`_devicescommands.md` (the wipe confirmation) and `_policies_passcode.md` ("not to
console passwords"), and none of them changes.

```
Expected-outcome: no-doc-impact
```

---

## Added on 2026-10-14 **[EVIDENCE]**

Six scenarios for kinds of merge request the first 24 lack: a large one, one with two
features, a revert, and three without a description. Real merge requests are often like
this. Every scenario has one change, at most 85 added lines and a clear description, which
names the trap in several cases. They are built from the fixture, not modelled on real
MobiVisor merge requests, which have not been looked at yet **[UNKNOWN]**. Run in repo mode, twice
each, on DocBot as on 2026-10-13 (Large 4, effort high). The runs are in
`devinfra/.runtime/experiments/messy-no-description-2026-10-14/`. 12 runs, $0.13.

| Scenario | Runner | On reading | What happened |
|---|---|---|---|
| `commands-tab-rework` | 1/2 | **0/2** | Run 1: triage answered no-doc-impact, calling **Retry** becoming **Resend** "internal refinements a reader would not rely on", although two pages name **Retry**. Run 2: **Resend** on both pages, the app installations' **Retry** left alone, but it also added a paragraph on paging and the empty state |
| `sprint-two-features` | 2/2 | 2/2 | Both features, on both pages, in both runs |
| `revert-device-export` | 2/2 | 2/2 | Heading and sentence removed; "Selecting a device's name opens its detail page." kept, now at the end of "Acting on several devices". Run 2 checked the Audit Log's **Export CSV** and left it |
| `invite-link-72h-no-description` | 2/2 | 2/2 | The same edit as with the description. It searched more: 11 and 13 conversation turns instead of 4 and 7, at about twice the cost |
| `kiosk-passcode-no-description` | 2/2 | 2/2 | Sentence corrected and **Exit passcode** step added, in both runs, as with the description |
| `lost-mode-dark-no-description` | 2/2 | 2/2 | Silent: triage read `lostMode: false` from the diff |

- **The description mattered less than expected.** All three variants were as right as their
  originals. Where the description had named the trap, DocBot found it in the code, at the
  price of more searching. Two runs each is thin: this rules out "usually breaks without a
  description", not "sometimes".
- **Size is the weak spot.** The one scenario that failed is the large one, once at triage
  and once by adding detail. In a 16-file diff, a label change in `en.json` reads as part of
  a refactor. This is a triage false negative, the second after `account-expiry` on
  2026-10-13. Triage's errors no longer all point one way.

## Why these new scenarios **[EVIDENCE]**

These are the gaps in the 24 built scenarios, checked against their patches and the
2026-10-13 runs:

- **Rules that appear, not change.** Both built time-limit scenarios change a number the
  manual already states. None tests a rule the manual has to gain, with no sentence to
  correct and no UI in the diff. Added: `inactive-accounts-disabled`.
- **Roles.** One permission moves (`helpdesk-update-os`), but no role is added, although
  three pages name the roles. Added: `enrollment-manager-role`.
- **Bug fixes that need an edit.** Both built bug fixes are negatives. When the manual
  describes a bug's effect, it has to change with the fix. Added: `apn-seamless-switch`.
- **Renames that over-match.** `retire-label` probes missing a form of the word. Nothing
  probes changing a word that means something else elsewhere. Added:
  `lock-screen-label`.
- **A second page without the changed word.** In every built scenario with two pages
  or more, each page contains the word that changed. The supervision list on
  `_enrollment_ios.md` does not contain "Ring", and the email list on `_settings.md`
  does not contain "disable". Added: `ring-ios-supervised`, `inactive-accounts-disabled`.
- **A fixed value that becomes a setting, a generated page, a new language, a mixed merge
  request:** no built scenario has any of these. Added: `audit-retention-setting`,
  `restriction-schema-only`, `french-ui`, `search-email-in-refactor`.
- **Pages.** No built scenario requires an edit to `chapter1.md`, `_groups.md`,
  `_apns.md`, `_policies_restrictions.md`, `_enrollment_android.md` or
  `_appinstallations.md`. The new ones require the first four. The last two are in
  "Considered and left out".
- **Facts the manual states more than once.** The demo README lists six. Three of them
  had no scenario: passwords of at least 8 characters, the session timeout, and the
  Apple Push certificate. `password-min-12` covers the first.
- **Harder negatives.** All 10 negatives were silent in both runs on 2026-10-13, so they
  no longer tell a better DocBot from a worse one. In the 2026-10-08 evaluation, false
  positives were the first weakness listed, and they came from changes that look
  visible. Each of the 5 new negatives looks visible.

## Considered and left out

| Scenario | Why not |
|---|---|
| Session timeout default from 30 to 15 minutes (`chapter1.md`, `_settings.md`) | Same shape as `password-min-12` and `command-expiry`: a number on two pages |
| Apple Push certificate warning from 30 to 60 days (`_dashboard.md`, `_settings.md`) | Same shape again |
| QR codes valid for 1, 7 or 30 days, chosen when created | It would cover `_enrollment_android.md`, but it repeats `invite-link-72h` (one of two parallel "7 days") and `audit-retention-setting` (a fixed value becomes a choice). It is the cheapest way to cover that page if page coverage matters |
| A **No licence** status for iOS app installations | It would cover `_appinstallations.md`, but it repeats the role's shape: a new item in a list the manual spells out |
| Removing the Auditor role | The mirror of `enrollment-manager-role`, with a rule that depends on it: imported accounts get the Auditor role. Worth adding once the new role has been measured |
| Replacing LDAP with single sign-on | It touches five pages and needs pages the manual lacks. That is what `wifi-policy` already tests, at several times the cost to build and judge |
| Deleting a flag after its release, or reverting an earlier scenario | It needs another scenario merged first. `open-test-mr.sh` and `test_live_update.py` apply each patch to a fresh `main` |
| The author edits the manual, but gets it wrong | By design, DocBot leaves pages edited in the merge request alone, so this would test reviewing, not drafting |
| A layout change that only makes screenshots stale | The fixture has no stylesheet and no running console, and the E2E suite recaptures screenshots. There is nothing for DocBot to do or get wrong |
| A new error message, such as for a duplicate email address on Add user | Its expectation depends entirely on question 41. `signin-messages-wording` probes the same boundary with an expectation that the current manual decides |

## Building them

Each new scenario is a commit in a clone of the fixture, exported as described under
"Adding one" in the scenarios README, into its group's folder:
`inactive-accounts-disabled` goes to `scenarios/time-limits/`, for example. The
**Expected** paragraph becomes the `Expected:` line, and the code block holds the other
lines.

- Write the title and description as a developer would, without mentioning the manual.
  A reason in a description above, such as a security review or a support request, is
  there to make the merge request realistic, not to give a hint.
- None of the new scenarios changes the fixture itself, so the built patches still
  apply.
- Keep what a scenario relies on out of the fixture. In repo mode, drafting can
  `grep` and `read_file` every tracked file at the merge commit, including
  `demo-repo/README.md` and `tools/docbot/`. So the traps these scenarios set
  (supervision requirements on two pages; "lock" as a command or as a locked account;
  "inactivity" of a session or of an account) belong here, not in the fixture's
  README.
- Once a scenario is built, add it to its folder's table in the scenarios README.
