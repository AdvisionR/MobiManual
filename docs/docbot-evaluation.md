# DocBot — what it is good and bad at, and how often triage is wrong

**Status:** evaluation, 2026-10-08. Answers the first two points of roadmap item 1 in
[current-state.md](current-state.md), "Test docbot extensively": what DocBot is good at
and what it is not, including its errors, its misses and new functionality, and whether
triage gives false positives, with the two ideas listed there: "even if unsure, forward
to proposal" and a three-way triage answer.
**Relationship to other documents:** builds on "Progress" in
[the Mistral prototype doc](docbot-mistral-prototype.md), whose 2026-10-08 Medium runs on
the first 11 scenarios are reused here. Nothing in DocBot's code was changed. Tags as in
the foundation doc: **[DECIDED]**, **[EVIDENCE]**, **[PROPOSED]**, **[UNKNOWN]**.

---

## Short answer

- **Good at [EVIDENCE]:** changing an existing page when the change alters a fact it
  states: a number, a permission, a label, a step, a removed button. This includes facts
  on several pages, and the right one of two similar sentences on one page. Also good at
  staying silent on code-only changes, including ones built to look like doc changes.
  Every merge that needed a manual change was found. The drafts are small and mostly
  exact.
- **Bad at [EVIDENCE]:**
  1. **Changes that look visible but change nothing a reader of the manual sees.**
     Triage answered `doc-impact` on 4 of the 14 fixture negatives, every time, and on
     7 of 58 random Zulip commits. Drafting stopped about half of those. The other half
     became edits: true but unneeded, padded with edge cases, or invented.
  2. **New functionality that needs a page the manual lacks.** DocBot cannot create
     pages, and no outcome tells anyone that a page is missing. A new screen either ends
     silently or gets stand-in sentences spread over existing pages.
  3. **Restraint and detail.** Edits to pages that were still true, one invented
     permission, one invented example. Every run missed one page that uses another form
     of the renamed word. The re-wrapper leaves orphan words in 3 of 76 drafts.
- **Triage false positives: yes, many, and none were false negatives.** Triage found all
  42 fixture runs with doc impact, and on 2026-10-01 all 9 Zulip ones. Its errors all
  point one way.
- **"Even if unsure, forward to proposal" is already what triage does.** A prompt rule
  saying so changed no fixture answer, and one Zulip answer in 58. What it costs depends
  on drafting, which is only half a filter.
- **The three-way answer sorts the fixture's doc-impact cases correctly**:
  `new-doc-needed` for exactly the two scenarios that need a new page, 6 of 6 runs. But today that answer has nowhere to
  go (see "New functionality").

Cost: $4.80 on `mistral-medium-3-5`, plus the $1.01 of the reused morning runs.

## What was tested

**The fixture**, now 24 scenarios **[EVIDENCE]**. The 11 existing ones, and 13 written
for this evaluation in `devinfra/scenarios/`, aimed at what the first 11 did not
cover:

| Scenario | Kind | What it probes |
|---|---|---|
| `invite-link-72h` | change a fact | Two "48 hours" on `_users.md`; only one changes |
| `helpdesk-update-os` | change a fact | A one-line permission change that makes two tables wrong |
| `wipe-confirm-name` | change a fact | A sentence made wrong by a label and a setting |
| `auditlog-export-removed` | removal | Deleting a sentence, and correcting the one that depends on it |
| `settings-branding` | new functionality, existing page | A new section on `_settings.md` |
| `wifi-policy` | new functionality, new page | A sentence to correct, and a page that does not exist |
| `locations-page` | new functionality, new page | Only a page that does not exist |
| `retire-identifiers` | negative | The mirror of `retire-label`: renamed in code, label unchanged |
| `auditlog-to-date-fix` | negative | A fix where the manual says nothing either way |
| `tr-label-fix` | negative | Turkish labels only |
| `a11y-labels` | negative | Template and `en.json` changes only screen readers notice |
| `ring-duration-documented` | negative | The author already edited the only page that states the fact |
| `drop-account-expiry` | negative | Removing a feature that was never switched on |

The new scenarios ran twice in each mode (repo mode, and `--diff-only`), through
`update_manual` with GitLab replayed from git, as `test_live_update.py` does. The first
11 ran three times in each mode that morning, once for the two that stop at triage. Triage alone ran three more times on every
scenario and comment kind, for each prompt variant.

**Zulip**, a random sample **[EVIDENCE]**. The fixture's negatives were written to
probe for errors, so they cannot say how often triage is wrong in practice. Seed
20261008 drew 60 of the 981 commits since 2026-04-28 that change no help page and keep a
file after the ignore list. Triage ran on each against the 464-page help centre. The
earlier Zulip negatives were chosen by their subject line, so they only showed silence
on obvious refactors.

**The ground truth is mine, and that is a limit [UNKNOWN].** I wrote the 13 scenarios
and their `Expected:` lines, and I classified the Zulip answers by hand. For Zulip, a
commit counts as needing no help change when its author changed no help page and no
later commit changed the page it would affect. Every one of the 7 was checked that way.

**Medium, not the cheaper Large 3.** The question is how the production model behaves.
Large 3 triages differently: 1 of 30 on `account-expiry`. Repetitions were kept low
instead.

## Bullet 1: what DocBot is good and bad at

### Results by scenario

"Pages" counts runs where the edited pages were exactly the expected ones.
"Content" is my reading of each draft.

**Worth documenting:**

| Scenario | Runs | Pages | Content |
|---|---|---|---|
| `command-expiry` | 6 | 6 | Both pages, 24 → 72 hours, 6 of 6 |
| `invite-link-72h` | 4 | 4 | The new-account link changed, the reset link's 48 hours left alone, 4 of 4 |
| `helpdesk-update-os` | 4 | 4 | Both tables right, 4 of 4 |
| `wipe-confirm-name` | 4 | 4 | Sentence corrected, not added to, 4 of 4 |
| `auditlog-export-removed` | 4 | 4 | Both sentences, 4 of 4. One run left a double blank line |
| `devices-filter` | 6 | 6 | Filter added, screenshot flagged, 6 of 6 |
| `passcode-history` | 6 | 6 | Table row, 6 of 6. One run added a paragraph with orphan words |
| `settings-branding` | 4 | 4 | Branding section with exact labels, placed in the console's order, 4 of 4 |
| `ios-department` | 6 | 6 | Step added 6 of 6; that **Finish** waits for a department, 4 of 6 |
| `kiosk-passcode` | 6 | 6 | Sentence corrected 6 of 6, screenshot flagged 6 of 6, exit-passcode step 4 of 6 |
| `account-expiry` | 6 | 5 | Repo mode found the field and its label, 3 of 3. `--diff-only`: `needs-human` 2, `no-change` 1 |
| `wifi-policy` | 4 | 2 | Type count corrected 4 of 4. Unneeded `_groups.md` edit 2 of 4. Missing page named 2 of 4 |
| `retire-label` | 6 | 0 | Three pages right, the author's page left alone; the Roles table's "retiring" missed 6 of 6 (question 37) |
| `locations-page` | 4 | 0 | Stand-in edits 3 of 4. The fourth: no edit, missing page named, ends `no-change`, so nobody hears |

**Not worth documenting:**

| Scenario | Runs | Silent | What happened otherwise |
|---|---|---|---|
| `refactor`, `apns-retry` | 2 each | 2 each | — |
| `retire-identifiers`, `tr-label-fix`, `a11y-labels`, `ring-duration-documented` | 4 each | 4 each | — |
| comment kinds (`code`, `internal`, `unmapped`, `both`, `ci`) | 3 each | 3 each | triage-only runs |
| `dashboard-count-fix` | 6 | 0 | Triage `doc-impact`; drafting read three pages and changed nothing, 6 of 6 |
| `drop-account-expiry` | 4 | 0 | Triage `doc-impact`; drafting `no-change` 3, `needs-human` 1 (a screenshot worry) |
| `auditlog-to-date-fix` | 4 | 0 | Triage `doc-impact`; drafting added "the **To** date includes the whole day", 4 of 4 |
| `lost-mode-dark` | 6 | 0 | Triage `doc-impact`; drafting documented the hidden command, 6 of 6, and gave Helpdesk a permission the code does not grant, 1 of 6 |

### Good at **[EVIDENCE]**

- **A fact that changes, wherever the manual states it.** Numbers, permissions, labels,
  confirmations, removed buttons: 22 of 22 runs over five scenarios, with the right
  pages and the right sentences. That includes facts on two pages, two tables at once,
  and one of two similar sentences on a page.
- **Additions that fit a page that exists**: a step, a filter, a table row, a section.
  The labels are copied from `en.json`, and the new text sits where the console puts
  the control.
- **Silence on what only the code sees**: 20 of 20 runs on the six negatives with nothing
  for a reader, plus every comment kind. That includes a rename of "retire" in the code
  and a change to an already-edited page.
- **Facts outside the diff, in repo mode**: `account-expiry`, 3 of 3.
- **Screenshots that may be stale are flagged** wherever the UI changed (`kiosk-passcode`,
  `devices-filter`, `retire-label`).

### Errors and misses **[EVIDENCE]**

| # | Kind | Where | What | Cause |
|---|---|---|---|---|
| E1 | Wrong edit | `lost-mode-dark`, 6 of 6 | Documents a command behind a flag that stays off | Triage passes it, and drafting writes what the diff shows. One draft notes the flag and documents it anyway |
| E2 | Invented | `lost-mode-dark`, 1 of 6 | Helpdesk may send Lost mode; `permissions.js` does not grant it | A guess from "supervised-only, like **Clear passcode**" |
| E3 | Invented | Zulip `7c14f7ecc9` | An example says `channel:automated testing` opens **#automated testing**; the commit message says it still parses as channel plus keyword | Drafted from a triage false positive |
| E4 | Unneeded edit | `auditlog-to-date-fix` 4 of 4; Zulip digest and Slack-import commits | True sentences at a level of detail the page never had. The Slack one adds rare error cases to the main steps, and one consequence the commit does not state | Triage false positive, then drafting finds something to say |
| E5 | Over-reach | Zulip `3cd35142d5` | A keyboard tip for one icon, pasted into 5 help pages | As E4 |
| E6 | Unneeded edit | `wifi-policy` 2 of 4 | Rewrites `_groups.md`'s example, which was still true | "Smallest edit" is in the prompt and not kept |
| E7 | Stand-ins | `locations-page` 3 of 4 | Mentions of the new page in chapter 1, the Roles table and `_devices.md`; one in the paragraph about the language menu | No page to write to, and no way to say so that anyone hears |
| E8 | Miss | `retire-label` 6 of 6 | The Roles table's "retiring" | Searches for `Retire\|Retired`, never the stem (question 37) |
| E9 | Partial | `kiosk-passcode` 2 of 6, `ios-department` 2 of 6 | The new step, or the rule that **Finish** waits | Run-to-run variance; the sentence edits are always there |
| E10 | Silent | `locations-page` 1 of 4, `account-expiry` diff 1 of 3, every `needs-human` | Missing page or doubt written only into `result.json` | See "New functionality" |
| E11 | Format | 3 of 76 drafts | Orphan words: `When`, `and`, `single-app kiosk mode` alone on a line | `edits.py` breaks too-long lines and never joins the rest onto the next line. The model wrapped at about 85 characters |
| E12 | Format | 1 of 76 drafts | A double blank line where a sentence was deleted | The replacement was an empty line |
| E13 | Not sent | Zulip, 2 of 60 | Dependency upgrades with `pnpm-lock.yaml` or `uv.lock`, 600k to 720k characters of diff | No ignore entry for lock files, and no size limit. The sweep held them back; DocBot would send them |

### New functionality **[EVIDENCE]**

It depends on whether the manual already has the page:

| Case | Result |
|---|---|
| An existing page gets a new section (`settings-branding`) | Good: 4 of 4 |
| A new console page, and a sentence elsewhere that becomes wrong (`wifi-policy`) | The sentence is corrected 4 of 4; the missing page is named in uncertainties 2 of 4 |
| A new console page, nothing else (`locations-page`) | Never `needs-human`. 3 of 4 spread stand-in sentences; 1 of 4 does what the prompt asks, and the outcome is `no-change` |

Three things in the design make this worse than the model's answers alone:

- **DocBot cannot create a page**, by design (README, "Flow").
- **Uncertainties reach a reader only inside an opened docs merge request.** With no
  edit, `update.py` ends at `no-change`, and the missing page stays in `result.json`.
- **`needs-human` reaches nobody either.** The `Jenkinsfile` archives `result.json`, and
  `needs-human` exits 0. Only `opened` produces something a person sees.

So for a new screen, the best answer DocBot can give today is one nobody reads.

## Bullet 2: triage false positives

### How often **[EVIDENCE]**

| | Doc impact found | False positives |
|---|---|---|
| Fixture, 14 positive and 14 negative scenarios and kinds, 3 runs each | 42 of 42 | 12 of 42: `lost-mode-dark`, `dashboard-count-fix`, `auditlog-to-date-fix`, `drop-account-expiry`, every run |
| Zulip, 58 random commits sent to the model | — | 7 of 58, 12% (95% interval about 6% to 23%) |
| Zulip, 9 commits whose authors edited help (2026-10-01) | 9 of 9 | — |

- **Triage is deterministic on the fixture.** All 29 cases gave the same answer three
  times out of three under every prompt. One triage run per case is enough there.
- **The Zulip seven**, each checked against the help page it would touch:

  | Commit | Change | Why it is a false positive |
  |---|---|---|
  | `3cd35142d5` | "Other views" icon reachable by keyboard | Accessibility; no help page mentions the icon |
  | `7c90102fa8` | Tab focus trapped in the reminders overlay | Accessibility |
  | `e51cc28c66` | No LDAP password asked of externally verified users | A registration edge case no page describes |
  | `5221b3b103` | Slack import shows an error instead of a 500 | Error handling |
  | `7c14f7ecc9` | Typeahead offers multi-word channel names | Visible, but the search page stays true |
  | `12ecdbe4a6` | Digest leaves out muted topics | Visible in an email, but the digest page stays true |
  | `d15d6f7af3` | `zerver/openapi/zulip.yaml` documents two endpoints | The API documentation, not the help centre |

- **At the scale of a commit stream**, about 12% of 981 commits is roughly 120 false
  positives, against about 15 commits whose authors edited help in the same commit. That
  is commits, not merge requests, and Zulip splits a feature over several commits.
  MobiVisor's merge requests will have a higher share of real doc impact **[UNKNOWN]**.
- **Why**, as far as the reasons show:
  - Triage sees the page headings, not their text, so it cannot check what a page says.
    For `drop-account-expiry` it gave as its reason that the field "is documented in
    the Users > Adding a user section". The manual never mentioned it.
  - Anything that looks like UI counts as visible. The flag is in the
    `lost-mode-dark` diff (`lostMode: false`), and triage still says users "will see
    and interact with this new command".

### What happens to a false positive next **[EVIDENCE]**

The idea "even if unsure, forward to proposal" relies on drafting catching what triage
let through. It does about half the time:

| False positive | Drafting |
|---|---|
| `dashboard-count-fix`, `drop-account-expiry`, Zulip registration, focus trap, API docs | Read the pages, changed nothing: harmless, $0.01 to $0.02 each on the fixture, $0.04 to $0.06 on Zulip |
| `auditlog-to-date-fix`, Zulip digest | One true sentence nobody needed: a docs merge request to close |
| Zulip Slack import | Edge cases in the main steps, one stated consequence the commit does not support |
| Zulip search | One invented example (E3) |
| Zulip "Other views" | A tip in 5 pages (E5) |
| `lost-mode-dark` | Documents a command users do not have; once with an invented permission |

Fixture: 2 of 4 stopped. Zulip: 3 of 7 stopped. Drafting a Zulip false positive cost
$0.04 to $0.17.

### "Even if unsure, forward to proposal" **[EVIDENCE]**

The `lean` variant added one rule to the triage prompt: when unsure whether a reader
would notice, answer `doc-impact`.

| | Baseline | `lean` |
|---|---|---|
| Fixture, 87 triage runs | 42 of 42 found, 12 false positives | the same answers, run for run |
| Zulip, the same 58 commits | 7 `doc-impact` | 8: also `753082fd05`, a regex engine swap for linkifiers |

Medium already forwards whatever it is unsure of. There is no recall left to gain at
triage, and the one extra Zulip answer could be run-to-run variance. Whether to forward
is therefore not a triage question. The question is what forwarding costs downstream,
and the table above answers it: about half the forwarded false positives become a docs
merge request a reviewer has to close.

### The three-way answer **[EVIDENCE]**

The `tristate` variant answers `no-doc-impact`, `modify-doc-needed` or `new-doc-needed`,
with `new-doc-needed` "even if existing pages need changes as well".

- **On the scenarios with doc impact it is exact, 42 of 42**: `new-doc-needed` for
  `wifi-policy` and `locations-page` (6 of 6), `modify-doc-needed` for the other 12.
  Drafting named the missing page in only 4 of 8 runs.
- **False positives are unchanged**, 12 of 42. `lost-mode-dark` comes back as
  `new-doc-needed`, though Lost mode would fit `_devicescommands.md` if it were on.
- **It cannot say "both".** `wifi-policy` needs a correction and a page. Read as a
  route, `new-doc-needed` would skip the correction drafting gets right 4 of 4.
- **It has nowhere to go yet.** `new-doc-needed` means "a human writes a page". Today
  nothing reaches a human unless a merge request opens (see "New functionality").

## What this suggests

### Make the outcomes without a merge request visible **[PROPOSED]**

Both ideas from the roadmap depend on this, and so do new pages. A short note on the
source merge request, with the outcome, the missing page and the uncertainties, would
reach the author, who knows the change best.

| Option | Verdict |
|---|---|
| **A note on the source merge request** | **Proposed.** It reaches the person who knows the change. It needs the API scope DocBot already has to open merge requests; whether the token may write notes is the Premium question in [current-state.md](current-state.md) |
| Mark the Jenkins build unstable | **Rejected.** Nobody watches post-merge builds, and coalescing hides some of them |
| A GitLab issue per finding | **Rejected for now.** Heavier, and an issue nobody owns goes stale |
| Leave it in `result.json` | **Rejected.** That is today's state, and E10 shows its cost |

### Find missing pages: at triage, at drafting, or both **[UNKNOWN]**

| Option | For | Against |
|---|---|---|
| Three-way triage | 6 of 6 on the fixture; cheap | Cannot say "both"; decided before a page is read; `lost-mode-dark` misfiled |
| A `missing_pages` field in `submit_proposal`, and an outcome rule (any missing page → the note above, edits still opened) | Decided after reading the manual; keeps the corrections | Untested; as free-text uncertainty it caught 4 of 8 |
| Triage's three-way answer passed to drafting as a hint, plus the field | Uses the stronger detector and keeps the edits | Untested; two places to keep in sync |

The third looks strongest on this evidence. Testing it takes `wifi-policy`,
`locations-page` and `settings-branding`, about $0.50 at two runs per mode **[PROPOSED]**.

### Lower the false positives at triage **[PROPOSED]**

The four fixture kinds and the four Zulip kinds suggest what to try (question 36):

- Rules for the kinds seen: hidden flags, fixes that match the manual, error handling,
  accessibility, and API documentation.
- Page text for the pages triage names, with a quote that is checked. Tested below.
- The repo and manual search tools (question 35).

### Follow-up: triage with page text and a checked quote **[EVIDENCE]**

Tested the same day, as two variants of triage in
`devinfra/.runtime/experiments/eval-2026-10-08/quote.py`. DocBot's code is unchanged.
Both answer `doc-impact` only with evidence of one of three kinds:

- `wrong`: a sentence of a page the change makes false, quoted;
- `missing`: what a reader now lacks, with the passage it belongs next to, quoted;
- `new-page`: what a page the manual lacks would describe.

A quote that is not on the page, whitespace aside, goes back to the model as a refusal.
The variants differ in how triage gets the text:

| Variant | How triage gets the text | Suits |
|---|---|---|
| `quote-text` | The whole English manual in the prompt, before the change: about 4k tokens on the fixture | A manual the fixture's size |
| `quote-tools` | The table of contents as today, plus `read_page` and `search_manual`, at most 8 calls | Any size: Zulip's help centre is about 225k tokens |

| | Baseline | `quote-text` | `quote-tools` |
|---|---|---|---|
| Fixture positives found | 14 of 14 | 14 of 14 | 14 of 14 |
| Fixture false positives, 14 negatives × 2 runs | 8 of 28 | 4 of 28 | 5 of 28 |
| Zulip positives found | 9 of 9 | — | 8 of 9: one ran out of its 8 calls |
| Zulip baseline false positives still `doc-impact` | 7 of 7 | — | 5 of 7; 1 fixed, 1 ran out of calls |
| Cost per triage, fixture / Zulip | $0.002 / $0.024 | $0.008 / — | $0.008 / $0.06 |

What the quote fixes, and what it does not:

- **It fixes claims the page itself disproves.** `dashboard-count-fix` (the page already
  says retired devices are not counted) and `drop-account-expiry` (the page never
  mentions the field): `no-doc-impact` in every run of both variants. `quote-text` also
  got `auditlog-to-date-fix` right in both runs.
- **It does not fix "the page could say more".** Every remaining false positive on both
  sets is `missing` evidence with a real quote. Examples: "the page does not explain
  that the To date now includes the entire day", or, for `apns-retry`, that pushes are
  now retried. On Zulip, 5 of the 7 false positives came back this way: accessibility,
  error handling, and detail below the page. A check in code can confirm that a quote
  is on the page, not that the reader needs what it says is missing.
- **It does not fix `lost-mode-dark`.** The model names the flag ("users will notice this
  command once the flag is enabled") and answers `doc-impact` with real quotes, in every
  run of both variants.
- **It broke one case: `ring-duration-documented`, 2 of 2 with `quote-text`.** The quote
  is the sentence the author already corrected in this merge request. One answer's own
  `why` ends with "no doc impact remains", and still says `doc-impact`.
- **The tools variant can run out of calls**: 2 of 16 Zulip runs searched for all 8
  calls and never answered, one of them a real positive. That would be `needs-human`,
  which nobody sees today. On the fixture it also made more `missing` claims than
  full text did (`apns-retry`, `auditlog-to-date-fix`).
- **Prompt caching works across runs of the same merge.** The second fixture run of each
  case cost a third of the first, because the commit, and with it the cache key, was the
  same. Across different merges the key differs, so nothing is shared. Placing the manual
  first, under a key that changes only with the manual, would let every merge reuse it
  **[UNKNOWN]**, untested.

**Verdict [PROPOSED]:**

- **Keep the evidence, and stop expecting it to cut false positives on its own.** It makes
  every `doc-impact` point at a page and a passage, which roadmap item 1 asks for under
  "Show exact reasons during triage". It refuses invented claims, and drafting could
  start from it.
- **The real-world false positives need a narrower `missing`.** Candidates, each
  testable for under $1 a round:
  - `missing` only for a new control, step or setting the change adds, with its label
    taken from the diff and checked there in code. That would remove most Zulip false
    positives, which add no label. But `account-expiry`'s label is not in its diff,
    only in the code.
  - The rules for the kinds seen (flags, accessibility, error handling).
  - A refusal for quotes from lines this merge request added to a page, aimed at
    `ring-duration-documented`.
- **Prefer full text where it fits.** On the fixture it cost the same as the tools, never
  ran out of calls, and had fewer false positives. It was not run on Zulip, whose help
  centre does not fit. How large MobiVisor's real English manual is decides whether it
  fits **[UNKNOWN]**.

Cost: $1.54, on `mistral-medium-3-5`.

### Second follow-up: what counts as missing **[EVIDENCE]**

The `missing` claims of the first follow-up split cleanly:

- **On the real positives, each claim names a new thing a reader works with**: a filter,
  a step, a field, a setting, a section, a permission, a menu action or a shortcut.
- **On the false positives, each claim describes how something the manual already
  covers now behaves**: retries, an inclusive date, topics left out of a digest,
  typeahead matching, keyboard focus, an error message.
- **The exception is `lost-mode-dark`**: a new command, but behind a flag that stays off.

That gives the narrowed definition, tested in two rounds as `narrow.py` in the same
directory. DocBot's code is unchanged.

**Missing** is a new thing a reader operates, usable as soon as the change merges: a
field, button, menu item, option, setting, filter, step, command, permission or
shortcut. It is missing when a page describes the screen or task it belongs to and does
not mention it. A change to how something already documented behaves is not missing:
it counts only if it makes a sentence false (`wrong`).

Each rule the code checks, and why:

| Check | Refuses | Aimed at |
|---|---|---|
| `missing` and `new-page` carry a label, found on a line the change adds | A label the change does not contain | Detail claims with nothing new to name; an invented label ("Expiration date" for **Account expires**) |
| The label is not on a line the change removes | Labels of things the change only modified | Zulip "Other views": an existing icon made keyboard-accessible |
| The label is not only in comments | Examples in code comments | Zulip `channel:automated testing` |
| A change that switches something on may give that line as its label | — | `account-expiry`: the field's label is in `en.json`, the diff is the flag |
| A `wrong` quote is not from lines this merge request added to the page | The author's own corrected sentence | `ring-duration-documented` |

The first round had only the first and last checks. The second added the middle three
(`narrow2-*`). The Zulip results are single runs.

| | Baseline | `narrow2-text` | `narrow2-tools` |
|---|---|---|---|
| Fixture positives found | 14 of 14 | 28 of 28 (2 runs) | 14 of 14 |
| Fixture false positives | 8 of 28 | **0 of 28** | 2 of 14 |
| Zulip positives found | 9 of 9 | — | 9 of 9 |
| Zulip baseline false positives still `doc-impact` | 7 of 7 | — | **1 of 7** |
| Cost per triage, fixture / Zulip | $0.002 / $0.024 | about $0.006 uncached / — | about $0.008 / $0.04 |

- **On the fixture, full text plus the narrowed `missing` is right in every run**, 56
  of 56. That includes `lost-mode-dark`, by the definition alone ("usable as soon as
  the change merges"), and `ring-duration-documented`, by the author-line refusal.
- **Without the flag-line rule, `account-expiry` was lost** in both first-round runs: the
  model invented the label "Expiration date", and the refusal sent it to
  `no-doc-impact`. With the rule, it gave `accountExpiry: true` and was right twice.
- **On Zulip, the one false positive left is the Slack import's new error message.** It
  gave the HTML id `slack-import-error` as its label. That id is new and outside a
  comment, so the code cannot refuse it, and an error message is not a thing a reader
  operates.
- **The tools variant slips on judgement where full text does not**:
  - `lost-mode-dark` in both rounds, reading "usable as soon as merged" as "usable once
    the flag is on";
  - one `drop-account-expiry` run that called still-true steps `wrong`.

  `wrong` has no check beyond the quote existing.
- **The call limit, raised from 20 to 25 the same day, helped.** The tools variant got
  25 instead of the first follow-up's 8, and recovered `ae588277af`, which had run out
  at 8 calls. The longest Zulip triage took 21 calls.

**Verdict [PROPOSED]:**

- **The narrowed `missing` with its checks is worth taking into DocBot's triage.** It is
  the first variant that removes most false positives on both sets without losing a
  positive.
- **The evidence is tuned to the same 14 fixture negatives and 7 Zulip commits it is
  measured on.** Before adopting it, run it on fresh data:
  - a new random Zulip sample, compared with the baseline's 12%;
  - the 51 Zulip commits the baseline got right, where the tools variant could add new
    false positives, as `drop-account-expiry` showed;
  - more Zulip commits whose authors edited help.

  That is about $3 to $5.
- **Full text where the manual fits, tools where it does not**, as after the first
  follow-up. The size of MobiVisor's English manual decides **[UNKNOWN]**.

Cost of both rounds: $2.50.

### Smaller fixes

**Done on 2026-10-08 [DECIDED]**, with offline tests (133 pass; ruff and pyright clean):

- **`edits.py`** (E11): the words a break spills over join the next line of the same
  paragraph, which is broken in turn if it gets too long. They stay on a line of
  their own only at the paragraph's end or before a Markdown line break. The three
  drafts with orphan words come out clean when replayed.
- **Lock files** (E13): a `lock-files` entry in the fixture's `doc-map.json`
  (`package-lock.json`, `npm-shrinkwrap.json`, `yarn.lock`, `pnpm-lock.yaml`), and
  `pnpm-lock.yaml` and `uv.lock` in the Zulip replay's ignore list.
- **A size limit** (E13): more than 100,000 characters of diff after the ignore list
  (about 25k tokens) ends in `needs-human`, with no model call. The largest change with
  doc impact replayed so far is 37k characters. Of the 1,237 Zulip commits, only one
  would stop there besides the two lock-file upgrades: a 220k-character revert that
  restores a whole integration.

**Still open [PROPOSED]:**

- **Drafting restraint** (E4 to E7): a rule against edits to pages that are still true,
  and against detail the page does not have elsewhere. Score it on `wifi-policy` and
  the Zulip false positives.

## New open questions

Numbering continues from the Mistral prototype doc.

| # | Question | Blocks |
|---|---|---|
| 38 | Where should DocBot report what it does not open a merge request for: `needs-human`, missing pages, uncertainties? | Acting on new functionality; "even if unsure, forward" |
| 39 | Should missing pages be found at triage (three-way answer), at drafting (a field), or both? | The routing of `new-doc-needed` |
| 40 | How many false positives will reviewers accept? On Zulip, about half of 12% of commits would become docs merge requests to close | Whether triage precision has to improve before the real repository |
| 41 | Does MobiVisor's manual document accessibility, error messages and fixes below its level of detail? The answer defines what counts as a false positive | Triage rules; the scenarios' `Expected:` lines |

## Reproducing

Everything is in `devinfra/.runtime/experiments/eval-2026-10-08/`: the scripts, every
`result.json`, and the JSONL rows the tables come from. Run from
`devinfra/demo-repo/tools/docbot/` with `uv run --env-file .env python <script>`:

| Script | Runs | Output |
|---|---|---|
| `compare.py mistral-medium-3-5 2 fixture-new.jsonl <scenarios>` | `update_manual`, both modes | `fixture-new.jsonl`, `fixture-new/` |
| `fixture_triage.py mistral-medium-3-5 3 triage-<v>.jsonl`, with `TRIAGE_VARIANT=lean\|tristate` | Triage alone, drafting stubbed | `triage-{baseline,lean,tristate}.jsonl` |
| `zulip_sweep.py mistral-medium-3-5 60 20261008 zulip-baseline.jsonl` | Triage on the Zulip sample | `zulip-baseline.jsonl`, `zulip-lean.jsonl` |
| `zulip_draft.py mistral-medium-3-5 zulip-fp-draft.jsonl <commits>` | Drafting, diff mode, on the false positives | `zulip-fp-draft.jsonl` |
| `show.py <result.json ...>` | Prints triage's reason, each page's decision, uncertainties and the diff | — |

The 13 new scenarios are ordinary patches in `devinfra/scenarios/`, so
`test_live_update.py` and `open-test-mr.sh` pick them up unchanged. The 126 offline
tests pass.

Cost by step: new scenarios $0.83, triage variants on the fixture $0.53, Zulip baseline
$1.42, Zulip `lean` $1.42, drafting on the Zulip false positives $0.60.
