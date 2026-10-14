# DocBot — drafting alone, with page creation, against triage then drafting

**Status:** results, 2026-10-14, on the `remove-triage-add-create-pages` branch. DocBot
without its triage step, with page creation and in repo mode only, run on the whole
fixture suite. Mistral Large 4, reasoning effort high, 2 runs per case, 70 runs, $0.52 at
half price ($1.03 at list). The runs are in
`devinfra/.runtime/experiments/drafting-alone-2026-10-14/`.
**Relationship to other documents:** "before" is DocBot as measured in
[docbot-repo-mode-scenarios.md](docbot-repo-mode-scenarios.md) (the repo-mode runs of
2026-10-13) and under "Added on 2026-10-14" in
[docbot-scenarios.md](docbot-scenarios.md). How DocBot works now is in its README
(`devinfra/demo-repo/tools/docbot/README.md`). Tags as in the foundation doc:
**[EVIDENCE]**, **[UNKNOWN]**.

---

## Short answer **[EVIDENCE]**

- **70 of 70 runs pass the runner, against 66 of 70 before. On reading, 68 are right,
  against 64 before.**
- **No change that needs the manual is missed any more.** Before, 2 runs went silent
  where an edit was needed, both because triage could not see the code:
  `account-expiry` and `commands-tab-rework`. Now all 40 such runs edit or create.
- **Silence held.** All 30 runs that needed silence stayed silent, as before.
- **Both new-page scenarios create their page, in both runs**, with no stand-in on an
  existing page. Before, `wifi-policy` put Wi-Fi settings on `_settings.md` in both runs.
- **It costs less in all.** $0.52 against $0.72 for the same 70 cases. A change that
  needs no page costs about twice as much ($0.0044 against $0.0020) and takes longer
  (median 14 s against 3 s). A change that does costs less ($0.011 against $0.017) and
  is faster (median 24 s against 36 s).
- **2 runs per case is thin.** A 2/2 rules out "usually broken", not "sometimes broken".

## What changed in DocBot

- **No triage.** One conversation decides whether the change affects the manual and
  edits it. It searches the manual and the code before deciding, instead of judging from
  the diff and the manual alone.
- **Pages are created.** A proposal names the pages the manual lacks; once it is
  accepted, the model writes them in the same conversation, and DocBot adds them to
  `htmlDocPages`.
- **Repo mode only.** `--diff-only` is gone.

## Per case

Before is scored against the expectations of its day. `locations-page` then expected
`needs-human`; now it expects `_locations.md` created. `wifi-policy` now also expects
`_policies_wifi.md` created.

| Case | Before: runner | Before: reading | Now: runner | Now: reading | What changed |
|---|---|---|---|---|---|
| `account-expiry` | 1/2 | 1/2 | 2/2 | 2/2 | Run 2 before: triage stopped it, because the field the flag turns on is not in the diff. Now both runs grep the code and add **Account expires** |
| `commands-tab-rework` | 1/2 | 0/2 | 2/2 | 0/2 | Before: run 1 silent at triage; run 2 added paging. Now: **Resend** right in both runs, and both also describe paging (see below) |
| `wifi-policy` | 0/2 | 0/2 | 2/2 | 2/2 | Before: a stand-in edit to `_settings.md`. Now: "four types" and `_policies_wifi.md` after Restrictions |
| `locations-page` | 2/2 | 1/2 | 2/2 | 2/2 | Before: one run spent its 35 calls and named no page. Now: `_locations.md` after `_devices_id.md` in both runs, including where the menu entry is |
| The other 26 scenarios | 52/52 | 52/52 | 52/52 | 52/52 | Same results. Includes `sprint-two-features`, `revert-device-export` and the 3 no-description ones |
| The 5 comment kinds | 10/10 | 10/10 | 10/10 | 10/10 | Before ran without the code; now with it |

Totals: before 66 runner, 64 reading; now 70 runner, 68 reading.

## The one disagreement: paging on the Commands tab **[UNKNOWN]**

Both runs of `commands-tab-rework` add a paragraph on the history's paging (50 a page,
**Back** and **Next**) and its loading and empty states. The paragraph is accurate. The
scenario calls it unneeded, as below the manual's level of detail. The prompt counts a new
button a reader operates as missing from the manual, and **Back** and **Next** are
buttons, so the prompt and the expectation disagree. Either the expectation should
accept the paragraph, or the prompt should say that controls for paging or sorting a list
are below the manual's level. This is the open question of what counts as below the
manual's level (open question 41).

## Smaller findings **[EVIDENCE]**

- **One crash, fixed.** In one run the model left the empty `missing_pages` out of its
  proposal, although the schema requires it. Validation accepted that and the code after
  it did not, so the run ended in a `KeyError`. It is fixed and tested, and the case was
  run again.
- **Uncertainties are repeated.** When writing a new page, the model often repeats the
  uncertainties of its proposal, slightly reworded, so the docs merge request lists them
  twice.
- **The new pages follow the manual's style:** a title, an introduction, numbered steps
  where there is a task, labels from the code, and no images. The screenshots they need
  are named under uncertainties.

## Not measured **[UNKNOWN]**

- Zulip, and MobiVisor's own manual. A silent change now costs a drafting conversation,
  which grows with the table of contents and the searching, not with the whole manual.
- A change that tempts DocBot to create a page it should not. No scenario does yet; every
  scenario but two expects no page created, so each would have caught one.
- Whether these scenarios look like MobiVisor's real merge requests.
