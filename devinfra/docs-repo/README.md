# mobivisor-manual (fixture)

Not the real MobiVisor manual. This is a throwaway docs repository used to
exercise the second half of the DocBot prototype: the part where a detected
doc impact becomes a **merge request a human can review**.

It is deliberately shaped like the real thing, because the shape is what DocBot
depends on:

```
manual.yaml                      chapter order — see "Why no numbers" below
pages/                           the manual source, one Markdown file per section
  intro/security.md              class: human-only
  users.md, roles.md             class: ai-drafted
  enrollment/ios-abm.md          class: ai-drafted
  policies/kiosk-modes.md        class: ai-drafted
  reference/policy-settings.md   class: generated
images/registry.yaml             the orphan-screenshot registry (foundation doc §5.1)
doc-impact/pending/              the ledger — where DocBot's records land
```

Every page carries its content class (§6.4) in front matter. The class governs
what may touch the file:

| Class | Who edits it |
|---|---|
| `generated` | the build, from a schema. Never a human, never a model. |
| `ai-drafted` | the drafting agent, then a human reviewer. |
| `human-only` | a human. The agent must never edit these — §6.7 validates it. |

Front matter is the source of truth *for the file*; the doc map in the console
repository is the source of truth for *which code changes reach it*. The two
have to agree, and a validation gate that checks they do is the obvious next
lint to write.

---

## What DocBot does to this repository

Foundation doc §7 chose delivery model **B** — a bot-authored docs merge
request, linked back to the source one. §7 also says of model C, the batched
ledger: *"B and C combine: B detects, C writes."*

So a run of `docbot propose` puts exactly one file on a `docbot/mr-<id>` branch:

```
doc-impact/pending/mr-12.yaml
```

and opens a merge request for it. **No prose is drafted.** The drafting agent
is Phase 3 (§11) and does not exist yet.

That is not a placeholder standing in for the real thing. The record states
what changed in the product, which pages it puts in question, and what the gate
believed and why — including the model, the confidence and the reason. Reviewed
on its own it answers "does the manual need changing?", and either outcome is
progress: an edit on the same branch, or a closed merge request with a reason
attached, which is exactly the labelled data §6.3 wants.

`doc-impact/pending/` is a queue. A release-time run empties it into one
coherent set of edits — the "forty independent nudges produce forty
inconsistent voices" problem §7 raises under option C.

---

## Why no chapter numbers in the headings

§4 lists it as defect 1: the real manual bakes numbers into heading text
(`CHAPTER 5: POLICIES`), so inserting a chapter invalidates every subsequent
heading, anchor, and cross-reference — and an agent editing near one of those
headings makes plausible-looking edits in the wrong place.

This fixture shows the fixed state. Headings carry no numbers; order lives in
`manual.yaml`, and numbering is the build's job. The other §4 defects — the
hierarchy break after chapter 5, the empty heading, the duplicate `Edit Role`,
the misspelled `../seperate.css` — are simply absent here.

---

## What is missing on purpose

- **No build.** §12 question #3 (the real Markdown sources and build script) is
  still open, so there is nothing authentic to imitate. `docbot validate` — the
  build-plus-link-check gate of §6.7 — is blocked on the same answer.
- **No images.** `images/registry.yaml` carries a few real orphan filenames
  from `combined.html` to show the §5.1 shape, but the files themselves are not
  here and the perceptual diff (§5 step 3) needs the E2E capture set that only
  CI has.
- **No archived versions.** §2 says old versions are archived as-is; that is a
  release-process concern, not a DocBot one.
