# DocBot triage — the narrowed triage with and without its checks

**Status:** results, 2026-10-13. A re-reading of the 2026-10-08 runs behind "Second
follow-up: what counts as missing" in [docbot-evaluation.md](docbot-evaluation.md). No
model calls; no cost.
**Relationship to other documents:** answers one question about that follow-up: how
much of `narrow2`'s result comes from the checks in code, and how much from the prompt.
Since 2026-10-13, DocBot's triage keeps only the checks that the page exists and the
quote is on it ("Decisions of 2026-10-13" in [the prototype doc](docbot-mistral-prototype.md)).
Tags as in the foundation doc: **[EVIDENCE]**, **[UNKNOWN]**.

---

## Short answer **[EVIDENCE]**

- **Without its checks, `narrow2-text` misses no positive and has 2 false positives in
  28**, against 0 with them. Both are `ring-duration-documented`.
- **Most of the drop from the baseline comes before any check runs.** False positives on
  the fixture: 8 of 28 for the baseline, 4 with full text and quotes, 2 with the
  narrowed definition, 0 with the checks.
- **`lost-mode-dark` is answered `no-doc-impact` before any check**, in both `narrow2-text`
  runs.
- **On Zulip, `narrow2-tools` without its checks leaves 3 of the baseline's 7 false
  positives, against 1 with them.** The two it removes are the two commits the round-2
  checks were written for.
- **A check changed a decision in 8 runs:** right in 6, wrong in 2 (round 1's
  `account-expiry`). Every other refusal was followed by the same decision, with a
  corrected quote or label.

## How it was measured

- Every run records each `submit_triage` call, including those a check refused. The
  first call is the answer with the checks off: same model, same prompt, nothing checked
  yet. The accepted call is the answer with them on.
- Model `mistral-medium-3-5`. Runs in `devinfra/.runtime/experiments/eval-2026-10-08/`.
- Fixture: 28 cases reach triage, 14 with doc impact and 14 without. `kind-ci` stops
  before triage. Zulip: 9 commits whose authors edited help, and the 7 false positives
  of the baseline triage.
- **The prompt stays the same [UNKNOWN].** It still asks for quoted evidence and says
  that anything else is refused. A narrowed prompt with a plain decision and no evidence
  was not run.

## Fixture

| Variant | Runs per case | Positives found, off / on | False positives, off / on |
|---|---|---|---|
| `narrow2-text` | 2 | 28 of 28 / 28 of 28 | **2 of 28** / 0 of 28 |
| `narrow2-tools` | 1 | 14 of 14 / 14 of 14 | 2 of 14 / 2 of 14 |
| `narrow-text` (round 1) | 2 | 28 of 28 / **26 of 28** | 2 of 28 / 0 of 28 |
| `quote-text` (quote check only) | 1, negatives 2 | 14 of 14 / 14 of 14 | 4 of 28 / 4 of 28 |
| Baseline (no evidence, no checks) | 3 | 42 of 42 | 12 of 42, the same 4 cases every run |

Wrong answers with the checks off:

- `narrow2-text` and `narrow-text`: `ring-duration-documented` in each run.
- `narrow2-tools`: `lost-mode-dark` and `drop-account-expiry`, also with the checks on.
- `quote-text`: `lost-mode-dark` and `ring-duration-documented` in each run, also with
  the checks on.

## Zulip

One run per commit.

| Variant | Positives found, off / on | Baseline false positives still `doc-impact`, off / on |
|---|---|---|
| `narrow2-tools` | 9 of 9 / 9 of 9 | **3 of 7** / 1 of 7 |
| `narrow-tools` (round 1) | 9 of 9 / 9 of 9 | 4 of 7 / 4 of 7 |

- `narrow2-tools`, checks off: `3cd35142d5` ("Other views"), `7c14f7ecc9` (multi-word
  channel names) and `5221b3b103` (Slack import error).
- `narrow2-tools`, checks on: `5221b3b103` only.
- `narrow-tools`: `12ecdbe4a6`, `3cd35142d5`, `5221b3b103` and `7c14f7ecc9`, both ways.

## Runs where a check changed the decision

| Variant | Case | Off → on | Refused by |
|---|---|---|---|
| `narrow2-text` | `ring-duration-documented`, 2 runs | `doc-impact` → `no-doc-impact`, right | The quote is a line the author added in this merge request |
| `narrow-text` | `ring-duration-documented`, 2 runs | `doc-impact` → `no-doc-impact`, right | The same |
| `narrow-text` | `account-expiry`, 2 runs | `doc-impact` → `no-doc-impact`, **wrong** | The label "Expiration date" is on no added line. Round 2's flag-line rule was added for this |
| `narrow2-tools`, Zulip | `3cd35142d5` | `doc-impact` → `no-doc-impact`, right | "Other views" is also on a removed line; then "ellipsis" is on no added line |
| `narrow2-tools`, Zulip | `7c14f7ecc9` | `doc-impact` → `no-doc-impact`, right | `channel:automated testing` is only in comments; `channel:foo bar` is only in the title; then a malformed answer |

## Refusals that changed nothing

The model resubmitted the same decision with a corrected quote or label.

| Variant | Refusals | Runs | Kinds |
|---|---|---|---|
| `narrow2-text` | 4 | 4 of 56 | Label 2 (`account-expiry`); quote 2 (`ios-department`, `retire-label`) |
| `narrow2-tools` | 1 | 1 of 28 | Label (`account-expiry`) |
| `narrow-text` | 2 | 2 of 56 | Quote (`ios-department`) |
| `quote-text` | 2 | 2 of 42 | Quote (`ios-department`, `ring-duration-documented`) |
| `narrow2-tools`, Zulip | 9 | 7 of 16 | Label 6 (3 in `5221b3b103`, which stays wrong); label on a removed line 1; answer format 2 |
| `narrow-tools`, Zulip | 8 | 5 of 16 | Label 6, quote 2 |
