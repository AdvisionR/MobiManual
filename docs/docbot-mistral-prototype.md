# DocBot — what a working Mistral prototype needs

**Status:** implementation sketch, built through step 7 of the build order (see
"Progress"). Written 2026-09-30 against
`tools/docbot/` as it stands after the placeholder step. The Mistral facts come from the
`mistralai` 3.0.0 wheel, inspected locally, and from Mistral's documentation, read the
same day (see "What was checked").
**Relationship to other documents:** this puts two plans into one build order. It uses
[the LLM draft plan](docbot-llm-draft.md) (its steps 1, 2 and 4 to 8, and Mistral for the
prototype, **[DECIDED 2026-09-24]**) and [the repo-access doc](docbot-claude-repo-access.md)
(the Client-SDK loop, **[DECIDED 2026-09-30]**, and the `--context diff|repo` comparison).
It makes four small decisions of its own, all **[PROPOSED]**. Claude comes later, as a
second adapter behind the same seam, once question 30 is answered.

Tags as in the foundation doc: **[DECIDED]**, **[EVIDENCE]**, **[PROPOSED]**,
**[UNKNOWN]**, plus **[DOCS]** for upstream documentation not reproduced here.

## Progress

**2026-09-30: the harness and the drafting step are built**, in `tools/docbot/`: the
seam (`llm/__init__.py`), the Mistral adapter (`llm/mistral.py`), the loop
(`llm/agent.py`), the git tools (`drafting/repo.py`), the edits (`drafting/edits.py`)
and the drafting conversation (`drafting/proposal.py`). There are 50 offline tests,
and ruff and pyright are clean. Not built yet: `ignore.py`, `manual.py`, triage, and wiring into
`update-manual`. Steps 3 (in part), 5 (in part) and 7 of the build order remain.

Where the build differs from the sketch below:

- **The drafting step is `proposal.py`, not a reworked `draft.py`.** The placeholder
  stayed in place until the wiring step replaced it on 2026-10-01.
- **The prompt is a constant in `proposal.py`**, not a file under `prompts/`.
- **The modules sit in two packages**, not flat (2026-10-01). `llm/` holds the seam,
  the adapter and the loop, none of which knows about manuals. `drafting/` holds
  `proposal.py`, `repo.py`, `edits.py`, and since 2026-10-01 `triage.py`, `manual.py`,
  `ignore.py` and `change.py`. The live tests and their helper are in `tests/live/`.
- **`read_file` is capped at 500 lines**, not 300. The worst case is then about
  35k + 20 × 7k ≈ 175k tokens, still inside 256k.
- **An edit's `find` tolerates whitespace differences.** If the snippet is not in the
  page as it stands, it is matched word by word with any whitespace between the words,
  and it must still match exactly once. The first live run showed why: `_devices.md` is
  hard-wrapped, and the model wrote the wrapped sentence on one line seven times before
  it matched. After the change, the same scenario took one turn.
- **No `DOCBOT_LLM_PROVIDER` yet.** It comes with the second provider.
- **Connection failures arrive as `httpx2.TransportError`**, not as the SDK's own
  errors **[EVIDENCE]**, so the adapter catches both. `gitlab.py` stays the only module
  that sends requests with `httpx2` itself.

**The live run** (`pytest -m live`), `mistral-medium-3-5`, 2026-09-30 **[EVIDENCE]**.
The model was given the pages each scenario's `Expected:` line says triage picks.
Cost is at $1.5 per million input tokens, $0.15 per million cached input tokens and
$7.5 per million output tokens:

| Scenario | Mode | Turns | Result against `Expected:` | Tokens (in / cached / out) | Cost |
|---|---|---|---|---|---|
| `kiosk-passcode` | diff | 1 | Full match: sentence corrected, exit-passcode step added, `_kiosk_mode_1.png` flagged | 952 / 0 / 888 | $0.008 |
| `kiosk-passcode` | repo | 8 | Sentence corrected. No step added, screenshot not flagged | 12,139 / 0 / 554 | $0.022 |
| `ios-department` | diff | 1 | Department step added before Finish. Does not say that Finish needs one | 1,026 / 0 / 598 | $0.006 |
| `ios-department` | repo | 11 | As in diff mode | 18,315 / 2,944 / 550 | $0.028 |
| `devices-filter` | diff | 1 (8 before the whitespace fix) | Filter added to the paragraph, `_devices_id.md` no-change, screenshot flagged | 939 / 0 / 414 | $0.005 |
| `devices-filter` | repo | 10 | As in diff mode. One rejected submission (a page left out), corrected | 15,222 / 7,168 / 674 | $0.021 |

What it shows:

- **The harness works end to end**: tool calls, results, the rejection-and-correction
  path, and the budget.
- **Prompt caching hits across turns** in some repo-mode runs, but not all.
- **On this fixture, repo mode costs 3 to 4 times more and is not better.** In the
  kiosk case it was worse. The model searched for HTML templates the fixture does not
  have. That matches the repo-access doc's warning that the fixture cannot show what
  searching adds. The fifth scenario still has to be built.

**2026-10-01: triage, the wiring and the Jenkins key are built.** `drafting/ignore.py`,
`drafting/manual.py` and `drafting/triage.py` are new. `update-manual` now runs triage
and drafting in place of the placeholder, which is deleted, and opens a merge request
only when a page was edited. `--context diff|repo` and `--repo` are on the command line.
Compose, CasC and the Jenkinsfile carry the key (step 7). There are 84 offline tests,
and ruff and pyright are clean. What remains: a laptop `--dry-run` against the stack
(step 5, from your terminal), the fifth scenario, and the runs through Jenkins (step 8).
The changed `Jenkinsfile` and DocBot code reach the stack's GitLab only after
`./scripts/seed-project.sh`.

Where the build differs from the sketch, in addition to the points above:

- **`change.py` holds the task's opening**, the merge request and its diff, which both
  conversations start with.
- **A conversation that ends without a valid answer becomes `needs-human`**, for triage
  as for drafting, with the loop's reason. The LLM draft plan had `error` for triage.
  That outcome means exit code 1, which says "infrastructure" to Jenkins, and a model
  that never validates is a judgement problem. LLM errors (unreachable, refused) are
  still `error`, exit code 1, like `GitLabError`.
- **A missing `doc-map.json` or `gruntfile.js` at the merge commit is `error`**, not a
  crash.
- **The result has `files.sent` and `files.ignored`**, not `files_sent`.
- **Triage has no repo tools** in either mode. `--context` changes drafting only.
- **The Jenkins key path: unset is safe [EVIDENCE].** CasC reads
  `${MISTRAL_API_KEY:-}`. A throwaway container from the rebuilt image, booted without
  the variable, came up and held `docbot-llm-key` with an empty secret. DocBot treats
  an empty key as missing, so the stage stops with exit code 2. The stack's Jenkins,
  recreated with `demo-repo/tools/docbot/.env`, holds a 32-character key.
- **Mistral sometimes sends a tool call's arguments as its name too [EVIDENCE].** It
  happened in 3 of 18 conversations on 2026-10-01, every time with the correct
  arguments as well. The loop answered "no tool named …", and the model corrected
  itself on the next turn. The error now says what happened and names the tools.
  Guessing the intended tool was rejected, since repo mode has four.

**The second live run**, `pytest -m live -k update`, `mistral-medium-3-5`, 2026-10-01
**[EVIDENCE]**. Each case is committed onto the fixture, and `update_manual` runs on it
in dry-run mode against a GitLab replayed from that local repository. So triage picks
the pages itself, and only the HTTP to a real GitLab is not exercised. All 13 outcomes
match. Prices as above:

| Case | Mode | Outcome | Triage: pages, turns | Draft: turns | Against `Expected:` | Cost |
|---|---|---|---|---|---|---|
| `kiosk-passcode` | diff | dry-run | `_policies_kiosk.md`, 1 | 2 | Full match: sentence corrected, exit-passcode step added, `_kiosk_mode_1.png` flagged. One turn lost to the misnamed call | $0.031 |
| `kiosk-passcode` | repo | dry-run | `_policies_kiosk.md`, 1 | 15 | Sentence corrected. No step added, screenshot not flagged, as on 2026-09-30 | $0.039 |
| `ios-department` | diff | dry-run | `_enrollment_ios.md`, 2 | 1 | Department step added before Finish. Does not say Finish needs one | $0.013 |
| `ios-department` | repo | dry-run | `_enrollment_ios.md`, 1 | 10 | As in diff mode | $0.029 |
| `devices-filter` | diff | dry-run | `_devices.md` only, 2 | 1 | Filter added to the paragraph, screenshot flagged. Triage did not pick `_devices_id.md` | $0.010 |
| `devices-filter` | repo | dry-run | `_devices.md` only, 1 | 7 | As in diff mode | $0.014 |
| `refactor` | diff, repo | no-doc-impact | none, 1 | — | Match | $0.002 each |
| kinds `code`, `internal`, `unmapped`, `both` | diff | no-doc-impact | none, 1 | — | Match: silence | $0.002 to $0.004 each |
| kind `ci` | diff | skipped | — | — | Match: every file ignored, no model call | $0 |

The whole run cost about $0.15. What it adds to the first run:

- **Triage picks the expected page every time**, and stays silent on the refactor and
  on every comment kind. That is goal 3 at the model tier, without the stack.
- **The `both` kind is silent too.** Triage was told `_enrollment_ios.md` was already
  edited, and the code change was a comment.
- **Repo mode is still not better on this fixture**, as on 2026-09-30.
- **The whitespace-tolerant `find` has a side effect.** In `devices-filter`, the
  replacement is one long line where the page had two wrapped ones. The match ignores
  the wrapping, and the replacement does not restore it. A reviewer sees a paragraph
  re-flowed.

**A prompt rule for the wrapping does not fix it [EVIDENCE].** The drafting prompt
gained a rule on 2026-10-01: keep the page's line breaks, wrap `replace` like the page,
and do not join a paragraph onto one line. The scenarios ran again in both modes
(`-k update_scenario`, $0.14):

- **`devices-filter` is still re-flowed in both modes.** In repo mode the paragraph is
  one line, as before. In diff mode the model broke it once, after the first sentence,
  with a trailing space, and left the rest on one line of 141 characters.
- **The cause is in `find`, not in `replace`.** In all four drafts of `devices-filter`,
  two before the rule and two after it, `find` was the wrapped sentence written on one
  line. The model does not reproduce the page's line break, so it cannot know where
  the page wraps.
- **The rest is unchanged in substance**: the same pages, the same edits, `refactor`
  silent. `kiosk-passcode` in repo mode flagged the screenshot this time, which counts
  as run-to-run variance.
- **The new error for a misnamed call worked**, in the 2 of 6 drafts where it occurred.
  Each corrected itself on the next turn. The next run disproved this, see below.

The rule was removed again the same day, in favour of the fix below.

**`edits.py` restores the page's wrapping [DECIDED 2026-10-01].** After each edit,
every line the edit touched that the page's own wrapping could not have produced is
broken at the page's wrap width. Lines are only broken, never joined, so the text
around the edit keeps its line breaks. Single trailing spaces are dropped from those
lines; two stay, as a Markdown line break. The page's wrapping comes from its own wrapped
lines, the ones that continue onto a next line of the same paragraph:

- **The width**, where new breaks go, is the longest such line. It is a lower bound on
  the width the author wrapped at. `_devices.md` has one wrapped line, so its width is
  76.
- **The limit**, above which a line is broken, is the smallest of each such line's
  length plus the next line's first word, which did not fit. For `_devices.md` that is
  82. A line of 78 characters could have come from the author's own wrapping, so it is
  left alone.
- **Headings, table rows, images, fences and Pandoc title lines** neither wrap nor
  count as wrapped lines. List items do.

Where this differs from the proposal:

| Option | Verdict |
|---|---|
| Re-wrap only when `find` matched with whitespace ignored | **Rejected.** An exact `find` with a one-line `replace` breaks the wrapping the same way. How `find` matched only stands in for the real condition, a line that is too long |
| Break at the longest wrapped line, and above it | **Rejected.** That is only a lower bound, so adding two characters to the longest line would break it, where a writer would not |
| **Break above the upper bound, at the lower one** | **Chosen.** Only lines the page's wrapping could not have produced change |
| A fixed width, such as 80 | **Rejected.** It would wrap pages that do not hard-wrap. `_policies_kiosk.md` has no wrapped line, so it has no width, and nothing on it is re-wrapped. That is a known gap: a long new paragraph there stays one line |

**The re-run** without the rule, with the fix (`-k update_scenario`, 2026-10-01, $0.25)
**[EVIDENCE]**:

- **`devices-filter` comes out wrapped in both modes**, with the filter sentence
  inserted: three lines of at most 71 characters in place of two. `find` was again one
  line in both drafts. The fix works without the model's help. There are 98 offline
  tests now.
- **The rest is unchanged in substance.**
- **The misnamed call got worse, and the new error does not help.** In diff mode,
  `kiosk-passcode` took 10 drafting turns, 9 of them misnamed, at $0.12, against $0.03
  in the first run. `ios-department` took 5, with 4 misnamed. The prompt was the same as
  in the first run, so this is variance on Mistral's side. The shape is always the same:
  the model writes the call as text, `submit_proposal{…} } submit_proposal`. Mistral's
  parser puts that text, ending in the tool's name, into the call's name, and the
  submission, intact, into its arguments. A repair was proposed: when a name is not a
  tool, but its last word is one, treat the call as that tool. **Withdrawn the same
  day**: it patches the symptom. The experiment below looks for the cause first.

**Where the misnamed calls happen [EVIDENCE].** Across the three runs, all 18
misnamed calls came from conversations whose only tool is the submit tool:

| Conversation | Tools | With misnamed calls | Misnamed calls |
|---|---|---|---|
| Drafting, `--context diff` | `submit_proposal` only | 5 of 9 | 16 |
| Triage | `submit_triage` only | 2 of 28 | 2 |
| Drafting, `--context repo` | submit and the three repo tools | 0 of 9 | 0 |

`mistral-medium-3-5` is an alias of `mistral-medium-2604`, `magistral-medium-latest`
and `mistral-vibe-cli-latest` **[EVIDENCE]**, from the API's model list: a reasoning
model, and the one Mistral Vibe uses by default. Mistral Vibe was considered as a
replacement for DocBot's loop and rejected: it calls the same `chat.complete` API, and
answers an unknown tool name with `Unknown tool '…'`, as DocBot did **[EVIDENCE]**,
from the `mistral-vibe` 2.25.8 wheel. It also brings what the repo-access doc rejected
the Agent SDK for: about 100 dependencies, pinning `mistralai==2.6.0` and `httpx` 0.28,
telemetry on by default, remote configuration, and `AGENTS.md` and `.vibe/` read from
the working directory.

**The experiment on Mistral Large [EVIDENCE].** The same two conversations, the
diff-mode drafts and the triage of `kiosk-passcode` and `ios-department`, replayed 20
times per variant through `agent.run` and the real validators, on `mistral-large-2512`
($0.5 in, $1.5 out per million tokens), 2026-10-01. 650 conversations cost $0.27. The
variants are ways of asking for the submission:

| Variant | Request |
|---|---|
| `any` | Today's: `tool_choice="any"` |
| `auto` | `tool_choice="auto"`, Mistral Vibe's choice |
| `named` | The submit tool named in `tool_choice`, where it is the only tool |
| `strict` | `strict: true` on the function definitions |
| `named-strict` | Both |
| `serial` | `parallel_tool_calls=false` |
| `drop` | A response with a misnamed call is not sent back, but asked for again |
| `json` | No tools: `response_format` with the submission's JSON schema |

- **Large misnamed 1 call in 650**, and none in the 640 single-tool conversations, in
  every variant, `any` included. The one was in repo mode, a different shape: a line of
  `grep` output used as a tool name. The failure is Medium 3.5's, so this run cannot
  rank the variants. That takes the Medium run below.
- **Every variant gave a valid answer on the first turn**, except `json` triage: in half
  of the conversations the first answer named `policies_kiosk.md` or "Kiosk Modes"
  instead of `_policies_kiosk.md`, and the second was right.
- **The drafts were the same in every variant and every repetition.** On
  `kiosk-passcode` the sentence is corrected and the screenshot flagged 20 times out of
  20, but the exit-passcode step that Medium adds is missing 20 times out of 20. On
  `ios-department` the department step is added every time. Triage picked the right page
  every time.
- **A Large draft costs about $0.0005**, against $0.006 to $0.03 on Medium, and $0.12
  in the worst run. Large writes about 170 output tokens per draft, Medium 900 to 1,200.
- **In repo mode, Large did not search for `kiosk-passcode`**: 5 submissions in 1 turn.
  For `ios-department` it searched 12 to 16 turns, and 2 of 5 ran out of the 20 calls
  looking for HTML templates the fixture does not have.

**The fifth scenario, `account-expiry` (2026-10-01).** The repo-access doc's example
was a change whose *page* only the repository reveals. That cannot separate the two
modes: triage, which picks the pages, has no tools in either mode, and drafting may only
edit the pages triage picked. So the fifth scenario tests what repo mode can change,
the third gap in that doc's "What repo access buys": a fact the edit needs that sits
outside the diff. The fixture gains `public/app/features.js`, flags for features that
ship dark, and `public/app/users/users.html`, the Users template, whose Add form shows
an optional **Account expires** date while `FEATURES.accountExpiry` is on. The scenario
turns the flag on: a one-line diff, with a commit message that names the feature and
nothing about the form.

- **Expected:** triage picks `_users.md`. In repo mode the draft finds the field and
  adds an optional step to "Adding a user". In diff mode the draft cannot know the label
  or that the field is optional, so `needs-human` is the right answer, and an edit that
  names a field is invented.
- **First run, Large, once per mode [EVIDENCE]:** in repo mode, triage picked
  `_users.md`, and the draft grepped for "expir", read `users.html` and wrote the step
  with the exact label, in 3 turns. In diff mode, triage answered `no-doc-impact`: "This
  change only enables an existing account expiry feature for users, with no visible
  changes". The same call landed differently on the two runs. That makes **triage the
  limit for changes like this**: whatever drafting can find, a merge that triage passes
  over never reaches it. Whether triage should search too is a new open question,
  number 35.

**Medium against Large, and the fixes on Medium [EVIDENCE]**, 2026-10-01, $1.30 in all:

- **Part A, the fixes on Medium:** diff-mode drafts of `kiosk-passcode` and
  `ios-department`, 5 times each per variant (10 per variant).

  | Variant | Valid answer | Misnamed calls | Responses that also wrote the call as text | Output tokens | Cost per draft |
  |---|---|---|---|---|---|
  | `any`, today's | 9 of 10; one hit the 10-call cap after 10 misnamed calls | 10 | 19 of 19 | 2,378 | $0.023 |
  | **`named`** | **10 of 10, on the first turn** | **0** | **0 of 10** | **about 250** | **$0.003** |
  | `drop` | 10 of 10 | 2, hidden by asking again | 12 of 12 | 1,004 | $0.009 |
  | `json` | 3 of 10: "edit" without its edits, until the cap | — | — | 1,315 | $0.019 |

  Naming the tool stops the cause: Medium no longer writes the call out as text, and
  that text is what the misnamed calls came from. The drafts were as good as with
  `any`. The baseline went wrong in 1 of 10 conversations this time, against 5 of 9
  before, so the text duplication is the steadier signal.
- **Part B, every scenario end to end in both modes**, Large 5 times and Medium twice.
  Large missed the kiosk exit-passcode step every time, and in repo mode ran out of the
  20 calls on `devices-filter` 5 times out of 5 and on `ios-department` 4 times out of
  13. Medium submitted every time. Large lost 8 runs to rate limits and Medium 1 to the
  120 s timeout, which the adapter had no answer for.
- **Part C, triage on `account-expiry`, 20 times per model:** Large picked `_users.md`
  0 times out of 20, Medium 19 times out of 20.

| | Large | Medium |
|---|---|---|
| Misnamed calls | 1 in about 700 conversations | frequent with `any`; none with `named` |
| Triage, scenarios 1 to 4 | right every time | right every time |
| Triage, `account-expiry` | 1 of 30 | 23 of 24 |
| Kiosk exit-passcode step, diff mode | 0 of 30 | 19 of 19 |
| Cost per diff-mode draft | about $0.0005 | $0.003 with `named` |

---

## Decisions of 2026-10-01

**Mistral Medium 3.5 for DocBot [DECIDED 2026-10-01].** Large is about six times
cheaper per draft than Medium with `named`, and fails where the judgement is hard:
it passes over a feature that a flag turns on, at triage, where nothing is drafted
after it, and it leaves out a step the change needs. `DOCBOT_LLM_MODEL` stays
`mistral-medium-3-5`.

**Triage decides whether a merge affects the manual; drafting decides which pages
[DECIDED 2026-10-01].** This replaces the LLM draft plan's triage that names the pages
(its Decision 1) and this document's drafting on the pages triage named.

| Option | Verdict |
|---|---|
| Triage names the pages from the table of contents, drafting edits those (the LLM draft plan) | **Replaced.** Triage chooses pages from headings without reading them, and drafting cannot add a page triage missed |
| Drafting gets the whole manual in its prompt | **Rejected.** Zulip's help centre is 880 KB in 464 files; the real manual builds to 166 KB of HTML. It would not fit, or would cost the whole manual on every merge with doc impact |
| **Triage answers yes or no; drafting reads the table of contents, searches and reads pages with tools, and edits the ones it chooses** | **Chosen.** Drafting reads before it decides, and can follow a term across pages with `search_manual` |

What comes with it, built the same day:

- **`docbot.triage/2`** has only `decision` and `reason`. Triage still reads the
  table of contents **[PROPOSED]**: it is how triage knows what the manual covers, and
  on Medium it caught the flag case with it. Triage without the table of contents was
  not tried.
- **`docbot.proposal/2`**: drafting gets `read_page` and `search_manual`, plus the repo
  tools with `--context repo`, and may edit any page in the manual. It lists the pages
  it edits or that need a human, and may list pages it read and left as `no-change`.
  At most 5 pages may be edited in one proposal **[PROPOSED]**, a guard for the
  prototype that replaces triage's 3. Drafting cannot create a page; it says so in
  `uncertainties`.
- **Both prompts take the product's name**, MobiVisor by default, so the Zulip replay
  does not tell the model it documents a device management console.
- **The adapter names a lone tool in `tool_choice`** (Part A). Triage is now the only
  conversation with one tool; drafting always has the manual tools. **It retries 429
  and 5xx** through the SDK, with backoff up to 5 minutes, which this document planned
  and the first adapter left out. **Its timeout is 300 s**, up from 120.

**The fixture end to end on Medium with the new design [EVIDENCE]**, `-k update`, both
modes, $0.16 for 15 runs: every outcome matched. Drafting found the expected page
itself every time and edited no other page. It searched before reading: on
`kiosk-passcode` in diff mode it took `search_manual`, `read_page`,
`submit_proposal`. `account-expiry` came back `needs-human` in diff mode and an edit
in repo mode, "Optionally set an expiry date for the account.", which is right but
does not use the template's **Account expires** label. No misnamed calls.

**Zulip, replayed with the new design [EVIDENCE]**, `-k "zulip and not repo"`,
`mistral-medium-3-5`, 2026-10-01, $1.37 for 15 cases. The help centre before each commit
is the manual: 464 files, pages and includes, a table of contents of about 15k
tokens. `zulip/cases.json` gained 6 negatives, small commits whose subject marks them
as refactors or cleanups, and an ignore list in the place of `doc-map.json`:

| Commit | Change | Triage | Pages the author edited | Pages the model edited | Draft against the author's |
|---|---|---|---|---|---|
| `4996507536` | Recommended logo dimensions | impact | `include/_AddAWideLogo.mdx` | the same | **Misleading**: "displayed at up to 200×25" became 800×80, which is the new minimum upload size; the new aspect ratio is missing |
| `d1f9dab801` | Mirroring removed | impact | `docs/bots-overview.mdx` | the same | **The same edit** |
| `83e9a83e85` | Reporting a message sends a confirmation | impact | `docs/report-a-message.mdx` | the same | Right fact, as a line of its own instead of inside the step |
| `f4bb27444c` | Link previews can be hidden per message | impact | `docs/image-video-and-website-previews.mdx`, `docs/keyboard-shortcuts.mdx` | `docs/keyboard-shortcuts.mdx` | The shortcut is right; the new section on the other page is missing. $0.40, the costliest case: 14 changed files |
| `26e0f9f27f` | Popover of linked topics | impact | `docs/link-to-a-message-or-conversation.mdx` | none: ran out of the 20 calls | See the re-run below |
| `c4f5d48086` | Quote and forward hotkeys apply to a selection | impact | `docs/keyboard-shortcuts.mdx` | the same, and `docs/quote-or-forward-a-message.mdx` | **The same edit** on the first page. On the second, **invented**: menu items and headings renamed, which the commit did not change |
| `ae588277af` | Per-channel push notification default, and a new page | impact | 5 pages and includes, plus a new page | none: `needs-human` on 3 pages, one of them the author's | Right area. The labels are in templates the diff does not show, so it did not guess |
| `8da9cbf764` | `Ctrl+]` and `Ctrl+[` indent list items, and new pages | impact | `docs/format-your-message-using-markdown.mdx`, plus 3 new files | `docs/keyboard-shortcuts.mdx` | The author wrote a new page, which DocBot cannot. The shortcuts went onto the shortcuts page instead, twice |
| `7013f22bbd` | Legacy notifications skipped under E2EE | impact | `docs/mobile-notifications.mdx` | the same | **Partial**: the setting's renamed label only; the changed behaviour the author described is missing |
| 6 negatives | Refactors and a CSS cleanup | **no impact, 6 of 6** | — | — | $0.024 each |

- **Triage was right 15 times out of 15**, the dark-theme CSS cleanup included.
- **The model chose 6 of the 14 existing pages the authors edited**, and 2 others. 5 of
  the 14 belong to `ae588277af`, where it answered `needs-human` on the right area.
  Without it, 6 of 9.
- **Its drafts**: 2 the same as the author's, 1 right but placed differently, 1 a
  section close to the author's (`26e0f9f27f`, re-run below), 3 partial, 1 misleading,
  and 1 page with invented labels. Pages an author created are out of reach: DocBot
  cannot create pages.

**Two harness faults the replay found, fixed the same day**, with tests:

- **Page names.** `26e0f9f27f` spent 7 of its 20 calls on `read_page` with names it
  shortened, `link-to-a-message-or-conversation` for
  `docs/link-to-a-message-or-conversation.mdx`. `read_page` and the proposal now accept
  a name without its folder or extension when it fits one page, and an unknown name
  comes back with the closest ones.
- **Re-wrapping a line the author wrote.** In `8da9cbf764`, the replacement repeated an
  existing long line, and the re-wrap broke it, as a line the edit touched. Only lines
  the edit wrote are re-wrapped now; a line the page already had is left as it is.

**The re-run of those two cases [EVIDENCE]** ($0.30): `26e0f9f27f` now submits, and adds
"View links to and from a conversation" to the author's page, with the author's heading,
the same `<TopicActions />` steps and the same **View links** label. It leaves out
what "Links to" and "Linked from" show, and when the option appears. `8da9cbf764` adds
the two shortcuts once, and the long line stays as it was. Both still lost two turns to
short page names in `submit_proposal`, before the proposal accepted them too.

**What Zulip shows that the fixture could not:**

- **Finding the page works, writing the change is the harder part.** Triage and page
  choice held up; most shortfalls are in what the draft says.
- **An edited page the commit did not need is the costliest error.** The renamed menu
  items in `c4f5d48086` would mislead a reader if merged unread. The prompt says
  "never invent labels", and the model did anyway on a page it chose itself.
- **Diff mode cannot see labels in templates**, as on the fixture: `ae588277af`
  answered `needs-human` instead. Repo mode has not been run on Zulip yet.

**`result.json` holds the whole conversation [DECIDED 2026-10-01].** `docbot.triage/3`
and `docbot.proposal/3` add the system prompt and the task. Each call records the text
that went back to the model, as `result`, or `error` when it was refused, in place of
`result_chars`. So the archived `result.json` of a Jenkins build shows what the model
read, not only what it asked for. This came up after a scenario merge through Jenkins
(`ios-department`, build `main #2`): DocBot opened the docs merge request, then crashed
in the CLI's narration, which still read the `pages` triage no longer returns. The JSON
is printed after the narration, so that run left no record. `test_cli.py` now runs the
command on `update_manual`'s real results.

| Option | Verdict |
|---|---|
| `MISTRAL_DEBUG=1` in the Jenkinsfile | **Rejected.** It logs every request to the console, and each request repeats the whole conversation, so a 15-turn run logs the task 15 times. It shows Mistral's wire format, not DocBot's tools, and it would change with the provider |
| The raw request and response per turn, as the sketch above planned | **Rejected.** The same repetition, in the file instead of the log |
| **What DocBot sent and got back, once each** | **Chosen.** Provider-neutral, and each text is stored once. A tool result is capped at 500 lines of at most 300 characters. By its token counts, the `ios-department` run through Jenkins would have grown by about 10 KB **[PROPOSED]**; Zulip's 15k-token table of contents goes in twice, once per task |

---

## The question

> Sketch what is needed for a functioning prototype for the Mistral Adapter.

## What "functioning" means

The prototype is done when all four of these hold:

1. **On a laptop:** `docbot update-manual --sha <merge> --dry-run` prints a real diff of
   real manual pages, drafted by Mistral, for a scenario merge.
2. **Through Jenkins:** a scenario merge opens a docs merge request `docbot/mr-<iid>` that
   edits `public/doc/en/_*.md`, and `docbot-changes.md` is gone.
3. **Silence:** the `refactor` scenario and the comment kinds end as `skipped` or
   `no-doc-impact`, and no merge request opens.
4. **Both modes:** every scenario has been run with `--context diff` and
   `--context repo`, and each outcome is recorded against its `Expected:` line.

**Out of scope:** the Claude adapter (question 30), `validate` (the build as a gate),
page classes (question 27), translations (question 1), the queue, and `report`.

## Short answer: the parts

```
update-manual
  ├── resolve, skip docbot-generated, docbot/mr-<iid>          unchanged
  ├── ignore.py        pure    doc-map ignore list → the files that matter, or skipped
  ├── manual.py        pure    htmlDocPages + headings → table of contents
  ├── triage.py        model   a conversation whose only tool is submit_triage
  ├── repo.py          git     list_files, grep, read_file at the merge commit (only with --context repo)
  ├── agent.py         pure    the loop, for both calls: step → run tools → add results → until submit
  ├── draft.py         model   a conversation with the repo tools (or none) and submit_proposal
  ├── edits.py         pure    proposal + page texts → new page texts, or an error for the model
  ├── llm/__init__.py  pure    the seam: Conversation, Tool, ToolCall, ToolResult, Turn, choosing the adapter
  ├── llm/mistral.py   API     the only module that imports mistralai
  └── publish          API     one commit with every edited page, the description, the new outcomes
```

In numbers: about eight new or reworked modules, one new dependency (`mistralai`, 11
packages), three new settings, one Jenkins credential, and tests that need neither a
key nor the stack, except for one live smoke test.

---

## Decision A — one loop for both calls

Both triage and drafting are **conversations that end when the model calls a submit
tool**. Triage has one tool, `submit_triage`, and drafting has `submit_proposal` plus
the repo tools in `repo` mode. `agent.run()` drives both.

| Option | Verdict |
|---|---|
| Triage through `response_format` `json_schema`, and drafting through the loop | **Rejected.** That means two mechanisms, two validation-and-repair paths, and two things to port to Claude |
| **Both through the loop, each ending at a submit tool** | **Chosen. [PROPOSED]** A validation error goes back as a tool result, and the model tries again in the same conversation. That is the LLM draft plan's "one repair", generalised to "up to the turn limit" |

With Mistral, `tool_choice="any"` on every turn means the conversation can only end
through a tool call **[EVIDENCE]**: `ToolChoiceEnum` has `auto`, `none`, `any` and
`required`. So there is no need for the "please call submit" follow-up that Claude
needs.

## Decision B — where the inputs come from

| Option | Verdict |
|---|---|
| Everything through a local checkout (`--repo`) | **Rejected for now.** Then `--context diff` would need a checkout too, and the tests for `update.py` would need a git repository |
| Everything through the GitLab API, the tools included | **Rejected.** `grep` over the API needs GitLab's search, whose behaviour on CE was never checked. One call per `read_file` is slow |
| **The inputs through the API, as today. The repo tools through local git** | **Chosen. [PROPOSED]** The merge request, the diff, `gruntfile.js` and the pages come through `gitlab.py`, which the existing `Forge` fake already tests. Only `repo` mode needs `--repo PATH`, the checkout that contains the merge commit |

`repo.py` checks `git cat-file -e <sha>^{commit}` before the first call. If the commit
is missing, DocBot exits with code 2 and names the flag. In Jenkins the workspace is the
checkout **[EVIDENCE]**. On a laptop that means a clone of the stack's project,
refreshed with `git fetch`, run from your terminal.

## Decision C — one set of limits, sized for the smallest window

Mistral Medium 3.5 has 256k tokens of context **[DOCS]**, against 1M for Claude. The
worst case under the repo-access doc's caps is about 285k, which does not fit.

| Option | Verdict |
|---|---|
| Limits per model | **Rejected for the prototype.** The same scenario would then run under different limits on each provider, which confounds the A/B |
| **One set that fits 256k** | **Chosen. [PROPOSED]** At most 20 tool calls. `grep` returns at most 50 lines of 300 characters, about 5k tokens. `read_file` returns at most 300 lines, about 4k tokens. Worst case: about 35k + 20 × 5k ≈ 135k tokens |

The limits are named constants in `repo.py` and `agent.py`, with no configuration until
a second provider needs different ones.

## Decision D — the default mode

`--context diff` is the default **[PROPOSED]**, because it is the LLM draft plan's
decided baseline. `repo` is opt-in, until the comparison under "How to decide" in the
repo-access doc settles it.

---

## The seam

```python
# llm/__init__.py — provider-neutral, no SDK imports
@dataclass(frozen=True)
class Tool:
    name: str
    description: str
    schema: dict              # JSON Schema of the arguments

@dataclass(frozen=True)
class ToolCall:
    id: str
    name: str
    arguments: dict | None    # None if the model sent arguments that are not valid JSON

@dataclass(frozen=True)
class ToolResult:
    id: str
    name: str
    text: str
    is_error: bool = False

@dataclass(frozen=True)
class Turn:
    calls: list[ToolCall]
    text: str                 # anything the model said besides its calls
    usage: dict               # prompt, cached and completion tokens, provider-reported
    raw: dict                 # the response as JSON, for result.json

class Conversation(Protocol):
    def step(self) -> Turn: ...
    def add_results(self, results: list[ToolResult]) -> None: ...

def open_conversation(settings, system: str, task: str, tools: list[Tool], cache_key: str) -> Conversation:
    """Chooses the adapter by DOCBOT_LLM_PROVIDER. Only 'mistral' exists for now."""
```

**The adapter keeps the transcript**, in its own provider's format. Mistral needs its
assistant message with `tool_calls` sent back, and Claude will need its content blocks
sent back byte for byte. Neither format leaks into `agent.py`.

## The Mistral adapter

```python
# llm/mistral.py — the only module that imports mistralai
import json
from mistralai.client import Mistral
from mistralai.client.errors import MistralError, NoResponseError

class LLMError(Exception): ...   # lives in llm/__init__.py; the CLI maps it to exit code 1

class MistralConversation:
    def __init__(self, client: Mistral, model: str, system: str, task: str, tools: list[Tool], cache_key: str):
        self._client, self._model, self._cache_key = client, model, cache_key
        self._tools = [{"type": "function",
                        "function": {"name": t.name, "description": t.description, "parameters": t.schema}}
                       for t in tools]
        self._messages: list = [{"role": "system", "content": system}, {"role": "user", "content": task}]

    def step(self) -> Turn:
        try:
            response = self._client.chat.complete(
                model=self._model, messages=self._messages, tools=self._tools,
                tool_choice="any", prompt_cache_key=self._cache_key)
        except (MistralError, NoResponseError) as e:
            raise LLMError(f"mistral: {e}") from e
        message = response.choices[0].message
        self._messages.append(message)
        calls = [ToolCall(c.id, c.function.name, _arguments(c.function.arguments))
                 for c in message.tool_calls or []]
        return Turn(calls, message.content or "", response.usage.model_dump(), response.model_dump())

    def add_results(self, results: list[ToolResult]) -> None:
        for r in results:
            content = f"Error: {r.text}" if r.is_error else r.text
            self._messages.append({"role": "tool", "tool_call_id": r.id, "name": r.name, "content": content})

def _arguments(raw: dict | str) -> dict | None:
    if isinstance(raw, dict):
        return raw
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return None               # agent.py answers with a tool error instead of crashing
```

What the sketch fixes, and what is still to confirm when it is built:

| Item | Status |
|---|---|
| Import path `from mistralai.client import Mistral` (1.x used `from mistralai import Mistral`) | **[EVIDENCE]**, from the package's README |
| `chat.complete` takes `tools`, `tool_choice`, `parallel_tool_calls`, `prompt_cache_key`, `reasoning_effort`, `response_format` | **[EVIDENCE]** |
| `function.arguments` is `dict` or `str` | **[EVIDENCE]**, from `Arguments = Union[Dict[str, Any], str]` |
| `finish_reason` is one of `stop`, `length`, `model_length`, `error`, `tool_calls` | **[EVIDENCE]**. `length` and `model_length` become `needs-human`, "answer cut off" |
| Cached tokens in `usage.prompt_tokens_details.cached_tokens` **[DOCS]** | The SDK's `UsageInfo` has no typed field for it, but allows extra fields **[EVIDENCE]**. So it is read from `usage.model_dump()`, which the adapter already logs whole, and a missing value counts as 0 |
| Error classes `MistralError` (base of `SDKError` and the others) and `NoResponseError` | **[EVIDENCE]** |
| `Mistral(client=…)` takes an `HttpClient`, so tests could pass an `httpx2.Client` with a `MockTransport` | **[UNKNOWN]**. The parameter exists. Whether a plain `httpx2.Client` satisfies the protocol is checked when the adapter's test is written |
| `retry_config` and `timeout_ms` | Exist **[EVIDENCE]**. Set a 120 s timeout and the SDK's retries for 429 and 5xx at implementation time |
| Whether a cache hit happens across DocBot's turns | **[UNKNOWN]**, not guaranteed by Mistral **[DOCS]**. Logged per turn, so the first live run answers it |

**Cache key:** `f"docbot-{sha[:12]}-{step}"`, where `step` is `triage` or `draft`. That is
stable within one run, contains nothing secret, and differs between runs.

**Model:** `DOCBOT_LLM_MODEL=mistral-medium-3-5` **[PROPOSED]**, $1.5 input and $7.5
output per million tokens, 256k context, tool calling **[DOCS]**. Large 3 ($0.5 and
$1.5) is the cheaper comparison run.

## The tools, and what the loop does with them

`repo.py` is the repo-access doc's design with Decision C's caps: `git ls-tree`,
`git grep -n -I -E`, and `git show <sha>:<path>`, plus the `private` deny list from
`doc-map.json`. The submit tools' JSON schemas are the `docbot.triage/1` and
`docbot.proposal/1` shapes from the LLM draft plan.

`agent.run(conversation, handlers, max_calls)` returns either the validated submission
or a reason to stop. For each call it does one of four things:

- **Unknown tool, or arguments that are not JSON:** a tool error that says so.
- **A repo tool:** run it, and log the path and the result size.
- **A submit tool:** validate it. If it is valid, return it. If not, send a tool error
  naming the exact problem: a page not in the table of contents, or a `find` that
  occurs zero times or twice.
- **The limit reached:** stop with `needs-human`, "search did not converge".

## The rest of the pipeline

| Module | What it needs | From |
|---|---|---|
| `ignore.py` | The ignore list from `doc-map.json` at the merge commit → the files that matter. If none are left: `skipped` | LLM draft plan, Decision 1 |
| `manual.py` | Parse `htmlDocPages` from `gruntfile.js` with the same regex as `check-missing-doc.js` (`var htmlDocPages = \[…\]`), and read each English page's headings → a table of contents | LLM draft plan, Decision 1 |
| `edits.py` | Apply `find`/`replace` pairs, where each `find` must occur exactly once | LLM draft plan, Decision 2 |
| `update.py` | The new outcomes (`no-doc-impact`, `no-change`, `needs-human`), several files per commit (`gitlab.commit` already takes a list of actions), the description from both answers. `draft.py` loses `MANUAL_FILE` | LLM draft plan, Decision 4 |
| `cli.py` | `--context diff\|repo`, `--repo PATH`, and narration for the new outcomes | This document |
| `config.py` | `DOCBOT_LLM_PROVIDER`, `DOCBOT_LLM_MODEL`, `MISTRAL_API_KEY`. A missing one exits with code 2 before any call, as today | LLM draft plan, "Configuration and secrets" |
| Prompts | Two system prompts, for triage and drafting, as files in `src/docbot/prompts/`, read with `importlib.resources`. They are reviewed like documentation | This document |

**`result.json`** gets `triage` and `draft` sections. Each one records the provider and
model, and every turn: the tool calls, their arguments, the result sizes, the usage
including cached tokens, and the raw response. There is also a `files_sent` list. The
schema string moves to `docbot.update/2`, since the outcomes change.

## Tests: what runs without a key or the stack

| Test | How |
|---|---|
| `test_ignore.py`, `test_manual.py`, `test_edits.py` | Pure functions. The kind table of `open-test-mr.sh` becomes the parameters of `test_ignore.py` |
| `test_repo.py` | A temporary git repository built in the test: caps, the deny list, a missing sha, a binary file |
| `test_agent.py` | A `FakeConversation` that replays scripted `Turn`s: a valid submission, an invalid one then a fix, bad JSON, an unknown tool, the limit |
| `test_update.py` | The existing `Forge` fake plus `FakeConversation`: every outcome, several files in one commit |
| `test_mistral.py` | The translation both ways: `Tool` → Mistral's schema, a response with `tool_calls` → `Turn`, string arguments, `finish_reason` `length`. Through a mocked transport if `Mistral(client=…)` accepts one, otherwise by building the SDK's response models directly |
| Live smoke test | A `pytest` marker, skipped without `MISTRAL_API_KEY`: one triage conversation on the `ios-department` diff |

## Plumbing

- **Dependency:** `mistralai==3.0.0` in `pyproject.toml`, then `uv lock` and the export to
  `requirements.txt`, as in the README. That adds 11 packages, from 14 to 25, and no
  second HTTP stack **[EVIDENCE]**. Check that the hash-checked install still succeeds in
  the `devinfra` Jenkins image.
- **Key on a laptop:** `tools/docbot/.env`, which already reserves `MISTRAL_API_KEY`.
- **Key in Jenkins:** the LLM draft plan's step 7. Compose passes `tools/docbot/.env` as
  an optional `env_file`, CasC turns it into a `docbot-llm-key` credential, and the
  Jenkinsfile binds it with `withCredentials`, next to `docbot-gitlab-token`. What CasC
  does when the variable is unset is still **[UNKNOWN]**. Check it, because a bad CasC
  value crash-loops Jenkins at boot.
- **Jenkinsfile:** `DOCBOT_LLM_PROVIDER` and `DOCBOT_LLM_MODEL` in `environment`. Once
  `repo` mode is wanted in CI, add `--context repo --repo .`.

## Build order

| # | Step | Needs | Rough size |
|---|---|---|---|
| 1 | `ignore.py`, `manual.py`, `edits.py` and their tests | — | A day |
| 2 | The seam in `llm/__init__.py`, `agent.py`, `FakeConversation`, `test_agent.py` | — | Half a day |
| 3 | `triage.py`, the reworked `draft.py`, the prompts, `update.py` outcomes and description, `test_update.py` | 1, 2 | A day |
| 4 | `llm/mistral.py`, `config.py`, the dependency, `test_mistral.py` | 2 | Half a day |
| 5 | Live smoke test, then `--dry-run` on a laptop against the four scenario merges in `--context diff` | 3, 4, the key | An hour or two, from your terminal |
| 6 | `repo.py`, `--context repo`, `--repo`, `test_repo.py`, the `private` deny list | 2 | Half a day |
| 7 | Key plumbing: compose, CasC, Jenkinsfile | 4 | An hour or two |
| 8 | The fifth scenario, then every scenario in both modes through Jenkins, recorded against expectations with cost per run | 5, 6, 7 | Half a day |

Steps 1 to 4 and 6 need neither the key nor the stack. Step 5 is the first moment
Mistral is called.

---

## What was checked

| # | Check | Result |
|---|---|---|
| 1 | `mistralai` 3.0.0: `chat.complete` parameters | `tools`, `tool_choice`, `parallel_tool_calls`, `response_format`, `reasoning_effort`, `prompt_cache_key` **[EVIDENCE]** |
| 2 | `ToolChoiceEnum` | `auto`, `none`, `any`, `required` **[EVIDENCE]** |
| 3 | `FunctionCall.arguments` | `Union[Dict[str, Any], str]` **[EVIDENCE]** |
| 4 | `ChatCompletionChoice.finish_reason` | `stop`, `length`, `model_length`, `error`, `tool_calls` **[EVIDENCE]** |
| 5 | `ToolMessage` | `role: "tool"`, `tool_call_id`, `name`, `content`, and no error flag **[EVIDENCE]** |
| 6 | `UsageInfo` | `prompt_tokens`, `completion_tokens`, `total_tokens` typed, extra fields allowed. No typed `prompt_tokens_details` **[EVIDENCE]** |
| 7 | `Mistral.__init__` | `api_key`, `server_url`, `client`, `retry_config`, `timeout_ms` among others **[EVIDENCE]** |
| 8 | Package README import path | `from mistralai.client import Mistral` **[EVIDENCE]** |
| 9 | Dependency | `httpx2>=2.13.0`, 25 packages together with DocBot's current 14 **[EVIDENCE]** |
| 10 | `htmlDocPages` in the fixture | A `var htmlDocPages = [...]` literal in `gruntfile.js`, parsed by regex in `check-missing-doc.js` **[EVIDENCE]** |
| 11 | Medium 3.5: context, price, tools | 256k, $1.5 / $7.5, function calling and structured outputs **[DOCS]** |
| 12 | Prompt caching | `prompt_cache_key`, 64-token blocks, cached tokens at 10% of the input price, no guaranteed hit **[DOCS]** |

Not checked: any call to Mistral. Nothing was sent from this session.

## New open questions

Numbering continues from the repo-access doc.

| # | Question | Blocks |
|---|---|---|
| 33 | ~~Is the existing `MISTRAL_API_KEY` on a paid plan or on the free Experiment tier?~~ **Answered 2026-09-30: a paid plan, with usage credits**, so inputs are not used for training by default | — |
| 34 | Does Mistral's data processing agreement confirm EU hosting, and does prompt caching still work under ZDR? | The real repository on Mistral |
| 35 | Should triage get the repo tools in `--context repo`? Today it has none in either mode, so a change whose effect only the code shows, such as a feature flag (`account-expiry`), can end at `no-doc-impact` before drafting can search. Searching at triage costs on every merge that reaches the model, not only on those with doc impact | Repo mode's value on changes like `account-expiry` |
