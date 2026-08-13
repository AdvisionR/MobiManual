# Doc-impact ledger

`pending/` is a queue. DocBot writes one record per source merge request that
the gate decided affects the manual, each on its own `docbot/mr-<id>` branch and
each carrying a merge request of its own.

A record states three things:

- **what changed in the product** — the source merge request, its author, and
  the files it touched (paths only, never diffs)
- **which manual pages that puts in question** — resolved through the doc map,
  not guessed
- **what the gate believed and why** — tier, model, confidence, and the reason
  it gave

It does not state what the pages should say. Nothing here is drafted prose;
foundation doc §11 puts the drafting agent in Phase 3.

## What a reviewer does with one

Either outcome is a result:

- **The manual needs changing.** Edit the pages on the same branch. The record
  travels with the edit, so the merged history says why the change was made.
- **It does not.** Close the merge request with a reason. §6.6 makes "no change
  needed" a first-class permitted output, and §6.3 wants exactly this data:
  after a few weeks the closed records are a labelled dataset showing where the
  gate is wrong.

Nothing merges itself. §7 rejects auto-publishing to a customer-facing manual
outright, and §14.1 makes human review mandatory.

## Why a queue and not just edits

§7, on delivery model C:

> a manual is a narrative document, and forty independent nudges produce forty
> inconsistent voices.

The queue is what makes the alternative possible: at a release tag, one run
processes everything pending into a single coherent set of edits, in one voice,
and gets the release notes out of the same data. Records move from `pending/` to
an archive when that run consumes them.

Until that run exists, the queue is still worth having — it is the difference
between "somebody should check the manual" as a feeling and as a list.
