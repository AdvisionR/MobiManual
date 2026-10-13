# DocBot — Mistral Large 4 with `narrow2-text` triage, against Medium

**Status:** results, 2026-10-13. Two runs of the fixture suite on Large 4, compared
with Medium's runs of 2026-10-08:
- the first with `narrow2-text` patched in, $0.80 at Large 4's launch price ($1.60 at
  list);
- the second on DocBot as built from it, under "Ported into DocBot", $0.91 ($1.82).
**Relationship to other documents:** `narrow2-text` is described under "Second follow-up:
what counts as missing" in [docbot-evaluation.md](docbot-evaluation.md). Medium's weak
points are from that document. The checks are measured in
[docbot-triage-checks.md](docbot-triage-checks.md). Tags as in the foundation doc:
**[EVIDENCE]**, **[UNKNOWN]**.

---

## Short answer **[EVIDENCE]**

- **Large 4 fixes every drafting point Medium got wrong**: the Roles table in
  `retire-label`, the exit-passcode step, the rule that **Finish** waits for a
  department, and the missing pages in `wifi-policy` and `locations-page`. Each was right
  in 4 of 4 runs.
- **It loses `account-expiry` at triage, 4 of 4.** In 3 of those runs its first answer was
  right, and a check refused it.
- **Without the checks, its triage misses 1 positive in 56 and has no false positive in 48.**
- **It copies exactly**: 0 of 120 quotes and 0 of 93 `find` snippets wrong. But in 12
  triage answers it named a page by its title instead of its file name.
- **New faults in its drafts**: it wrote the merge request's plans into the manual (2 of
  4 runs), and added explanations the scenario did not ask for (3 of 4).
- **On scenarios that need an edit, it is 3.4 times slower than Medium.** It costs less
  at the launch price and 1.4 times as much at list price.

## How it was run

- `mistral-large-4`, still a public preview, alias `mistral-large-4-0`.
  `reasoning_effort` is not sent, so Large 4 reasons, as in the 2026-10-08 setting
  "Large 4". Whether the model behind the alias changed since then is **[UNKNOWN]**.
- Triage is `narrow2-text` with its checks: the whole manual in the prompt. Drafting is
  DocBot's own, with `MAX_CALLS = 35`.
- The fixture: 24 scenarios in repo mode and with `--diff-only`, and the 5 comment
  kinds, 2 runs each. That is 106 runs. Triage does not use the repository, so each
  case has 4 triage runs. `kind-ci` stops before triage.
- Medium is put together from runs that exist. Drafting comes from the 2026-10-08
  pipeline runs: 3 per mode for the first 11 scenarios, 2 for the other 13. Triage comes
  from its `narrow2-text` triage-only runs, 2 per case.
  - Drafting never sees triage's answer (`update.py`), so a positive's draft is the
    same under either triage.
  - The prompts have not changed since. The limits then were 20 or 25 calls, which
    Medium never reached, and 5 pages, which no fixture scenario reaches.
- Runs, runner and `summarize.py`: `devinfra/.runtime/experiments/large-4-narrow-2026-10-13/`.

## Triage

| | Medium | Large 4 |
|---|---|---|
| Runs per case | 2 | 4 |
| Positives found, checks off | 28 of 28 | 55 of 56 |
| Positives found, checks on | 28 of 28 | **52 of 56** |
| False positives, checks off | 2 of 28 (`ring-duration-documented`) | **0 of 48** |
| False positives, checks on | 0 of 28 | 0 of 48 |

**`account-expiry`** (the merge request switches a flag on, which shows a new field):

| Run | First answer | Refused because | Final |
|---|---|---|---|
| repo 0, repo 1 | `doc-impact`, label `accountExpiry` | The label is also on the removed line `accountExpiry: false` | `no-doc-impact` |
| diff 1 | `doc-impact`, no evidence | "doc-impact needs at least one piece of evidence; without any, the answer is no-doc-impact" | `no-doc-impact` |
| diff 0 | `no-doc-impact`: "only flips the internal FEATURES.accountExpiry flag" | — | `no-doc-impact` |

The rule that a flag line may stand in for the label is only in the text of the
"not on an added line" refusal. Large 4 was never refused that way, so it never saw that
rule. Medium was, and found the field.

**`lost-mode-dark`, `dashboard-count-fix`, `auditlog-to-date-fix`, `drop-account-expiry`**:
right in 4 of 4 runs on Large 4. Medium's `narrow2-text` triage is right on them as well.

## Drafting, on Medium's weak points

| Point | Medium | Large 4 |
|---|---|---|
| `retire-label`: "retiring" in the Roles table on `_users.md` | 0 of 6 | 4 of 4 |
| `kiosk-passcode`: a step for the **Exit passcode** | 4 of 6 | 4 of 4 |
| `ios-department`: **Finish** waits for a department | 4 of 6 | 4 of 4 |
| `locations-page`: `needs-human`, the missing page named, no stand-in edits | 1 of 4 | 4 of 4 |
| `wifi-policy`: the missing page named | 2 of 4 | 4 of 4, with an outline of the page from the code |
| `wifi-policy`: a page edited beyond `_policies.md` | `_groups.md`, 2 of 4: a rewritten example that was still true | `_settings.md`, 3 of 4: see below |
| `account-expiry`, repo mode: the field on `_users.md` | 3 of 3 | Never drafted |
| `account-expiry`, `--diff-only`: `needs-human` | 2 of 3 | Never drafted |

- **`_settings.md` in `wifi-policy`** adds Wi-Fi policies with WPA2 Enterprise to what the
  directory is used for. The change supports it: "Enterprise signs in with the device
  owner's directory account, so it needs a directory under Settings > Directory". The
  scenario's `Expected-` lines do not allow the page, so the runner fails these 3 runs.
- **By the runner's score** (outcome and pages), Large 4 passed 99 of 106 runs. On
  scenarios that need an edit, it passed 49 of 56; Medium passed 57 of 70.

## Other differences in the drafts

| | Medium | Large 4 |
|---|---|---|
| `auditlog-export-removed`: the merge request's plan in the manual ("it will come back as a background job that mails the file") | 0 of 4 | 2 of 4 |
| `passcode-history`: a sentence explaining the setting, besides the table row | 1 of 6 | 3 of 4 |
| `find` snippets not on the page | 5 of 149 | 0 of 93 |
| Triage quotes not on the page, `narrow2-text` | 2 refusals in 56 runs | 0 in 104 runs (120 quotes) |
| Triage evidence naming a page that is not in the table of contents | 0 | 12 refusals in 10 runs |

The 12 page names were titles ("iOS Enrollment", "Kiosk Modes", "Device Details"), file
names without the leading `_` (`policies.md`), or names with a note in brackets. Each was
resent with the right name. None changed a decision.

All 4 runs of the other 10 scenarios that need an edit were read. Apart from the first
two rows above, every fact in them is in the change: 72 hours, Helpdesk sending
**Update OS**, the device name to type before a wipe, the compliance filter, an exit
passcode of at least 4 characters, and the Branding section's PNG or SVG of at most 1 MB.

## Calls, time and cost

On the 14 scenarios that need an edit:

| | Medium | Large 4 |
|---|---|---|
| Median run | 8 s | 28 s |
| Slowest run | 42 s | 232 s |
| Cost per run | $0.018 | $0.013 at launch price, $0.026 at list |

- **No run ran out of calls.** The most calls one draft used was 27 (`wifi-policy`), then 24
  (`kiosk-passcode`). On 2026-10-08, with 20 calls, 7 of Large 4's 63 runs ran out.
- **No call passed the 300 s timeout.** On 2026-10-08, one did.

## Ported into DocBot

The second run, on 2026-10-13, is DocBot as built from the first. The runs are in
`devinfra/.runtime/experiments/large-4-port-2026-10-13/`. What differs from the first
run:

- **Triage is DocBot's own `docbot.triage/4`.** The prompt is `narrow2-text`'s, plus
  two sentences:
  - a flag switched on makes what it hid usable;
  - name each page as the manual does.
- **Only the checks that look something up are kept**: the page exists, and the quote is
  on it.
- **The drafting prompt** says to describe the product as merged, without its history
  or plans.
- **`reasoning_effort` is `high`**, sent with every request. It was unset in the first
  run.
- **The model is `mistral-large-4-0`**, an alias of `mistral-large-4`.

### Short answer **[EVIDENCE]**

- **The same score**: 98 of 106 runs, against 99. On scenarios that need an edit, 49
  of 56 both times.
- **The "as merged" rule worked**: the merge request's plans went into the manual in
  0 of 4 runs, against 2 of 4.
- **The flag sentence did not fix `account-expiry`**: 1 of 4, against 0 of 4.
- **Without the author-line check**, 1 false positive in 48 triage runs.
- **`locations-page` fell to 2 of 4**, from 4 of 4.

### Triage

| | Large 4 + checks | As built |
|---|---|---|
| Positives found | 52 of 56 | 53 of 56 |
| False positives | 0 of 48 | 1 of 48 |
| Refusals | 18: page names 12, missing labels 3, label on a removed line 2, no evidence 1 | 9, all page names |

**`account-expiry`:**

| Run | Answer |
|---|---|
| repo 0 | `doc-impact`, with the flag line as the label. The draft added the **Account expires** step |
| repo 1, diff 0, diff 1 | `no-doc-impact`. One reason: the flag "turns on account expiry that was already implemented but hidden; the manual never mentions account expiry, but the diff shows no new user-facing field" |

**`ring-duration-documented`, diff 0**: `doc-impact`, quoting "**Ring** plays a sound for
1 minute", the sentence the author had already corrected. Its own `why` says the change
"matches what the manual already says". Drafting changed nothing, so the outcome was
`no-change`.

### Drafting

| Point | Medium | Large 4 + checks | As built |
|---|---|---|---|
| `retire-label`: the Roles table on `_users.md` | 0 of 6 | 4 of 4 | 4 of 4 |
| `kiosk-passcode`: the **Exit passcode** step | 4 of 6 | 4 of 4 | 4 of 4 |
| `ios-department`: **Finish** waits for a department | 4 of 6 | 4 of 4 | 4 of 4 |
| `locations-page`: `needs-human`, the missing page named, no stand-in edits | 1 of 4 | 4 of 4 | 2 of 4 |
| `wifi-policy`: the missing page named | 2 of 4 | 4 of 4 | 4 of 4 |
| `wifi-policy`: `_settings.md` edited | 0 of 4 | 3 of 4 | 3 of 4 |
| `auditlog-export-removed`: the merge request's plan in the manual | 0 of 4 | 2 of 4 | 0 of 4 |
| `passcode-history`: a sentence explaining the setting, besides the row | 1 of 6 | 3 of 4 | 3 of 4 |
| `find` snippets not on the page | 5 of 149 | 0 of 93 | 0 of 92 |

`locations-page`'s two misses:
- `diff 0` added "Only administrators can open the Locations page." to `_users.md`.
- `repo 1` ran out of its 35 calls. Its outcome, `needs-human`, is the expected one, so
  the runner passes it, but it named no missing page.

### Calls, time and cost

On the 14 scenarios that need an edit:

| | Large 4 + checks | As built |
|---|---|---|
| Median run | 28 s | 31 s |
| Slowest run | 232 s | 356 s |
| Cost per run | $0.013 at launch price, $0.026 at list | $0.015 at launch price, $0.030 at list |
| Median output tokens | 1,421 | 1,374 |
| Runs out of calls | 0 | 1 of 106 |

No call passed the 300 s timeout.
