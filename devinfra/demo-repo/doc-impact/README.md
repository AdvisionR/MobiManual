# Doc-impact ledger

`pending/` holds one record per merged merge request that the gate decided
affects the manual. DocBot writes each on its own `docbot/mr-<id>` branch and
opens a merge request for it.

It sits at the repository root rather than under `public/doc/`, because
`public/` is the served web root and these records are not part of the manual.

A record states three things:

- what changed in the product — the source merge request, its author, and the
  files it touched
- which manual pages that puts in question, resolved through the doc map
- what the gate believed and why — tier, model, confidence, reason

It does not state what the pages should say.

## What a reviewer does with one

Either outcome is a result. If the manual needs changing, edit the pages on the
same branch, so the merged history says why. If it does not, close the merge
request with a reason: those closures are the data that shows where the gate is
wrong.

Nothing merges itself.

## Why a queue

A manual is a narrative document, and many independent edits produce many
inconsistent voices. Keeping records in a queue allows one run at a release tag
to process them into a single coherent set of edits, and to produce release
notes from the same data. Records move to an archive when that run consumes
them.
