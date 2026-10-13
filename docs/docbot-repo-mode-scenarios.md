# DocBot — repo mode, scenario by scenario

**Status:** results, 2026-10-13. These are the repo-mode runs from "Ported into DocBot" in
[docbot-large-4-narrow2.md](docbot-large-4-narrow2.md): DocBot as built, on Mistral
Large 4, 2 runs per scenario. The runs are in
`devinfra/.runtime/experiments/large-4-port-2026-10-13/`.

---

## Short answer **[EVIDENCE]**

- **45 of 48 runs pass by the runner's score, but only 44 are really right.**
- **20 of 24 scenarios were right in both runs.**
- **2 runs per scenario is thin.** A 2/2 rules out "usually broken", not "sometimes
  broken".

## How a run works

1. **Triage** reads the merge request's diff and the whole manual, then decides whether
   the manual is affected. It never sees the code.
2. **Drafting** edits the manual. In repo mode it can also search the code at the merge
   commit (`list_files`, `grep`, `read_file`). It has at most 35 tool calls.

## Per scenario

**Scenarios that need a manual change (14):**

| Scenario | What it tests | Repo mode | Notes |
|---|---|---|---|
| `auditlog-export-removed` | A removed button, and a sentence that depends on it | 2/2 | |
| `command-expiry` | A number on two pages | 2/2 | |
| `devices-filter` | A new filter | 2/2 | |
| `helpdesk-update-os` | A permission in two tables | 2/2 | |
| `invite-link-72h` | One of two "48 hours" on a page | 2/2 | |
| `ios-department` | A new step, and **Finish** waits for it | 2/2 | |
| `kiosk-passcode` | A corrected sentence and a new step | 2/2 | |
| `passcode-history` | A new table row | 2/2 | |
| `retire-label` | A rename on four pages | 2/2 | See the first example below |
| `settings-branding` | A new section on an existing page | 2/2 | |
| `wipe-confirm-name` | A sentence made wrong by a new label | 2/2 | |
| `wifi-policy` | A corrected sentence, plus a page the manual lacks | **0/2** | Both runs got the required edit right. Both also made a true edit to `_settings.md` that the scenario does not allow |
| `locations-page` | Only a page the manual lacks, so `needs-human` | **1/2** (runner: 2/2) | Run 1 used up its 35 calls and named no missing page. Its outcome, `needs-human`, is the expected one, so the runner passes it |
| `account-expiry` | A flag switched on shows a field the diff does not contain | **1/2** | Triage stopped run 1. See the second example below |

**Scenarios that need no change (10): all 2/2.** These are `a11y-labels`, `apns-retry`,
`auditlog-to-date-fix`, `dashboard-count-fix`, `drop-account-expiry`, `lost-mode-dark`,
`refactor`, `retire-identifiers`, `ring-duration-documented` and `tr-label-fix`.

## Example that succeeds: `retire-label`

**Task.** The merge request renames **Retire** to **Unenroll**, changing only the labels
in `en.json`. The author updated one page, `_devices.md`, and missed the others.

**Expected.** Rename Retire/retired on the four pages the author missed, including the
Roles table on `_users.md`. Leave `_devices.md` as the author wrote it.

**Received, both runs.** The same four pages, with `_devices.md` left alone. From run 0:

| Page | Before | After |
|---|---|---|
| `_devices_id.md` | **Retire** removes the device … A retired device disappears … | **Unenroll** removes the device … An unenrolled device disappears … |
| `_devicescommands.md` | `\| **Retire** \| yes \| yes \| Administrator \|`, and the bullet **Retire** removes the management profile … | The same, with **Unenroll** |
| `_dashboard.md` | Retired and wiped devices are not counted on any tile. | Unenrolled and wiped devices are not counted on any tile. |
| `_users.md` (Roles table) | Everything, including Settings, retiring and wiping devices, … | Everything, including Settings, unenrolling and wiping devices, … |
| `_devices.md` | — | No change: "Already updated in this merge request" |

The draft also noted, without being asked, that the screenshots on three pages may
still show the old label.

## Example that fails: `account-expiry`

**Task.** The merge request changes one line:

```diff
-    accountExpiry: false
+    accountExpiry: true
```

The field this flag turns on exists only in code the diff does not show.

**Expected.** Triage answers `doc-impact`. Drafting searches the code, finds the
optional **Account expires** field on the Add user form, and adds a step for it to
"Adding a user" on `_users.md`.

**Received, run 1.** Triage answered `no-doc-impact` with no evidence, so nothing was
drafted. Its reason:

> The change flips the internal `accountExpiry` feature flag from false to true […].
> However, the manual nowhere mentions account expiry […]. The feature's user-facing
> surface (e.g., an expiry date field on the Users form) is not described in the change
> itself […].

The triage prompt already says that switching a flag on makes what it hid usable, and
the model declined anyway. Repo mode cannot help here, because triage runs before
drafting and never sees the code.

**Received, run 0, for comparison.** Triage got it right, and drafting found the field
in the code:

```diff
 3. Choose a role. The role determines which pages the user can open.
-4. Select **Save**.
+4. Optionally set **Account expires** to a date. From that date the account
+   can no longer sign in to the console, and the devices the user enrolled
+   stay managed.
+5. Select **Save**.
```
