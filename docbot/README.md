# DocBot CLI

The standalone command line behind MobiManual DocBot. Foundation doc §8.5 is the
governing constraint: **no logic in Groovy**. Jenkins collects context, runs one
of these subcommands, and archives the JSON it produces. Everything here runs
identically on a laptop.

Implements Phase 1 and Phase 2 of §11 — the deterministic screenshot work and
the doc-impact gate — plus delivery model B from §7: a positive verdict opens a
merge request on the docs repository, linked back to the source one. No
drafting agent; that is Phase 3.

---

## 1. Quick start

```bash
uv sync
uv run pytest                                    # 68 tests, no network

# deterministic, no model, no spend
uv run docbot screenshots index --manual ../combined.html --out .docbot/image-index.json
uv run docbot screenshots audit --index .docbot/image-index.json

# the gate
echo "src/enrollment/ios/EnrollmentWizard.tsx" > changed.txt
uv run docbot gate --changed-files changed.txt --doc-map examples/doc-map.yaml \
  --mr 4 --title "Update iOS enrollment wizard copy" --out verdict.json

# what the gate would send to the docs repo, rendered but not written
uv run docbot propose --verdict verdict.json --docs-project root/mobivisor-manual \
  --doc-map examples/doc-map.yaml --dry-run
```

`MISTRAL_API_KEY` comes from `.env` at the repository root, or the environment.
`--no-model` runs tier 1 alone and never touches the network. `propose` needs
`FORGE_TOKEN` and `FORGE_URL` only when it has something to propose — not for a
`--dry-run`, and not for a `doc_impact: false` verdict.

For the whole pipeline against a live GitLab, see
`devinfra/scripts/docbot-run.sh`.

---

## 2. Commands

| Command | Does | Model? | Writes? |
|---|---|---|---|
| `gate` | Is this MR user-facing? Which manual areas? | tier 2 only | no |
| `propose` | Open the docs merge request for a verdict | no | the docs repo |
| `screenshots index` | Build the image→page index from the built manual | no | no |
| `screenshots impact` | Which pages does this MR put in question? | no | no |
| `screenshots audit` | Lint: orphans without registry entries, missing files | no | no |
| `eval` | Replay a labelled corpus, score the gate | optional | no |

Named in §8.6 and **not** built: `render-reference` (needs the policy schemas —
open question #7), `draft` (Phase 3), `validate` (needs the Markdown sources —
open question #3).

`propose` is not in the §8.6 list either; section 4 below says why it is a
command of its own rather than part of `gate`.

---

## 3. The gate

Three tiers (§6.3); this implements the first two.

**Tier 1 — path filter.** Pure lookup against the doc map. Costs nothing, drops
most merges. Escalates when a doc-relevant area is touched, *or when a changed
file matches no area at all*. That second rule is deliberate: it is how a stale
doc map becomes visible instead of silently suppressing the gate. Turn it off
with `defaults.escalate_unmapped: false` to trade the safety net for spend.

**Tier 2 — cheap model, structured verdict.** `{user_facing, areas, confidence,
reason}`, temperature 0, JSON mode. Area ids not in the doc map are rejected and
recorded as `rejected_areas` rather than trusted.

**Decisions that do not go to the model at all** (§14.2, deterministic beats
probabilistic):

- a `generated` area was touched → the reference tables are stale, full stop
- only `no-doc-impact` areas were touched → silent, tier 2 never runs
- a `human-only` area was touched → `human-review`, never `draft`
- tier 2 errored → `doc_impact: true` for human triage. A gate that crashes
  blocks merges.

### What is never sent to the model

File paths, the MR title, and the MR description. **Never diffs, never file
contents.** §10 flags "diffs from a proprietary MDM codebase will leave the
network" as an unresolved governance risk, and the gate does not need them to
decide whether a change is user-facing. A test asserts this
(`test_prompt_carries_no_diff_only_paths`). If sign-off arrives, adding diff
context is a change in `gate.py` and nowhere else.

### Every verdict is logged

Append-only JSONL at `.docbot/verdicts.jsonl` (§14.4 — "the data is the
output"). Eval replays log to `.docbot/eval/` so they cannot contaminate it.

---

## 4. The docs merge request

`docbot propose` takes a verdict and opens a merge request on the **docs**
repository. §7 chose delivery model B — "bot-authored docs PR, linked back to
the source PR. The destination."

It is a separate command from `gate` on purpose. The gate needs no write
access to anything, which is what makes it safe to replay a corpus of
historical MRs through it offline (§8.6) and cheap to run on every push. Only
`propose` holds a forge token, and the token it holds reaches one repository
that contains no product code.

### What lands in the docs repo

One file, on a branch named after the source merge request:

```
doc-impact/pending/mr-4.yaml       branch docbot/mr-4-<slug>
```

That is model **C**, the batched ledger, delivered through mechanism **B** —
§7: *"B and C combine: B detects, C writes."* The record states what changed,
which pages it puts in question, and what the gate believed and why. **It
drafts no prose**, because the drafting agent is Phase 3.

The merge-request body is written for a reviewer who has never heard of DocBot:
why it opened, what the model said and how confident it was, which pages are
implicated, and what to do — including that closing it is a correct outcome
(§6.6 makes "no change needed" first-class, and §6.3 wants that data).

### Rules it enforces

- **Silent verdicts never reach the forge.** `doc_impact: false` exits before
  the first API call (§6.2, §14.3).
- **The branch name is derived from the source MR id**, so the second, fifth
  and ninth push to a source MR all update one docs MR — body included —
  instead of opening nine. A reviewer who is shown nine learns to ignore all
  of them.
- **Never a commit to the docs default branch.** §7 rejects option D outright.
  `seed-docs-repo.sh` protects `main` on the GitLab side as well, so the rule
  survives a bug in this code.
- **Still no diffs.** The record carries changed *paths*, exactly as the gate's
  prompt does — the §10 governance question is still open, and a docs
  repository usually has a wider audience than the code one.
- **A failed courtesy comment does not fail the run.** `--comment-source` posts
  the §7-option-A advisory note back on the source MR; if the bot cannot, the
  proposal is still reported as created, with a warning.

Every proposal is logged to `.docbot/proposals.jsonl`, separately from
`verdicts.jsonl` so that delivery records cannot contaminate the gate's
evaluation dataset.

### The forge is behind an interface

§12 question #1 — GitLab, Bitbucket or GitHub Enterprise — is still open. §8.1
claims that choice "decides the plugin and nothing else"; `forge/` is where
that claim is kept honest. `gitlab.py` is 200 lines of REST, `fake.py` backs
both the tests and `--dry-run`, and nothing above them knows a GitLab URL.

Everything goes through the API rather than a git checkout, including the
commit: §8.4's warning that a multibranch job checks out a *merge commit* over
a shallow clone applies just as much to writes as to diffs.

---

## 5. Screenshots

The §5 chain, all deterministic:

```
changed E2E spec  →  screenshots that spec captures  →  manual chapters
changed image     →  manual chapters
```

Measured against the real `combined.html`:

| | |
|---|---|
| image references | 125 |
| unique images | 103 |
| E2E-derived (`<spec>-<test>.png`) | 53 |
| hand-captured orphans | 50 |
| chapters | 15 |

**Not implemented: the perceptual diff** (§5 step 3). It needs both image sets
side by side in CI, which the prototype does not have. `odiff`/`pixelmatch` with
a small threshold slots into `screenshots.impact()`; byte equality is too noisy
because of font rendering and timing. Until then `impact` reports screenshots as
*in question*, not as *stale* — the distinction is in the output.

A changed **source** file is deliberately not resolved to screenshots. Mapping
source → spec needs coverage data we do not have, and guessing produces exactly
the false positives §6.2 warns against.

### Filename convention gotchas

Both found by running against the real manual, both now tested:

1. **Test names contain hyphens.** `generaldeviceconfig_page-Should_save_e-mail_settings.png`
   is a test called "Should save e-mail settings". Split on the *first* hyphen
   only — the spec half is a filename stem and cannot contain one.
2. **Spec names contain `@`.** Some specs are parameterised by an account:
   `Single_Device_page_for__s3beyaz@boryazilim_com-should_start_within_correct_page.png`.

A third case is genuinely undecidable: `_iosApp_page-should_add_new_iosApp_page_1.png`
carries both the hand-captured `_` prefix and a test-shaped name. It stays
classified as an orphan — conservative, since the audit then demands a registry
entry — but is flagged `ambiguous` so a human resolves it rather than the parser
guessing.

---

## 6. Evaluation

`docbot eval` replays a labelled JSONL corpus offline and scores it (§8.6). This
is why the gate is a library with a CLI on top rather than logic in a
Jenkinsfile.

Against `tests/fixtures/corpus.jsonl` — 10 hand-written cases, 5 positive:

| | accuracy | precision | recall | FP rate |
|---|---|---|---|---|
| tier 1 only | 0.90 | 0.833 | 1.00 | 0.20 |
| tier 1 + `mistral-small-latest` | 1.00 | 1.00 | 1.00 | 0.00 |

The single tier-1 false positive is the unmapped-file rule firing on a pure
refactor — exactly the case tier 2 exists to clear, and it did.

**Read this result narrowly.** Ten hand-written cases that the same author also
wrote the doc map for is not evidence the gate works; it is evidence the
pipeline works end to end. The real corpus is the logged verdicts from a few
weeks of advisory-mode running (§6.3), and the false-positive rate is the number
to watch — §14.3 makes silence the common correct answer, so a false positive is
the expensive error.

---

## 7. Divergence from the foundation doc

**§10 says "Either OpenAI or Anthropic; both work. [DECIDED]". This uses
Mistral**, at the user's direction, because that is the API key available. The
doc asks that contradictions of a [DECIDED] item be stated explicitly, so:
stated. Nothing about the design depends on it — `providers/` is a one-method
interface and a second vendor is a new file (`providers/mistral.py` is 90 lines).
The §10 requirement that actually matters, keeping the provider swappable for
A/B comparison on the same corpus, is satisfied.

Three other notes:

- **§9 proposed Python.** Followed. The open dependency question (where the
  policy schemas live) is untouched — `render-reference` is not built.
- **The doc map is YAML** per §6.5. The loader also reads JSON, so the Jenkins
  prototype's existing `demo-repo/docs/doc-map.json` works unchanged and the
  eventual wiring is a one-line swap rather than a migration.
- **Page paths are `.md`, not the `.adoc` of the §6.5 sample.** §3.1 established
  from `combined.html`'s Pandoc metadata that the manual source is already
  Markdown — "no format migration is needed" — so the sample's extension
  predates its own document's evidence. Nothing depends on the extension; the
  fixture docs repository is Markdown to match.

---

## 8. Layout

```
src/docbot/
  cli.py           click entry point, one function per subcommand
  gate.py          tier orchestration, prompt, decision rules
  docmap.py        doc map loading + validation, tier 1
  propose.py       doc-impact record, MR body, open-or-update
  screenshots.py   filename convention, index, impact, audit
  manual.py        HTML parsing of the built manual
  evalharness.py   corpus replay and scoring
  verdictlog.py    append-only JSONL: verdicts, proposals
  providers/       one-method interface: mistral, fake
  forge/           merge-request interface: gitlab, fake
examples/doc-map.yaml
tests/             68 tests, all offline
```

`providers/fake.py` is a deterministic keyword stub. It is not good, and is not
meant to be — its value is that it is *stable*, so a failing test means the
pipeline broke rather than the model drifted. `forge/fake.py` is the same idea
for the write side, and doubles as `--dry-run`.

---

## 9. Not wired into Jenkins yet

The `Jenkinsfile` in `devinfra/demo-repo/` still runs the jq placeholder, and
the pipeline is driven from a laptop by `devinfra/scripts/docbot-run.sh` —
which runs the same two commands, with the same arguments and the same
artifacts, so the Jenkinsfile becomes a transcription of it.

What is left: install docbot into the Jenkins image, replace the jq block with
`docbot gate`, add a `propose` step guarded on `doc_impact`, and register
`MISTRAL_API_KEY` and `forge-bot-token` as Jenkins credentials. Note that
rebuilding that image re-resolves all plugins, which are unpinned — see
`devinfra/README.md` §7. Pin them in the same change.

One decision to make when it is wired: §8.3 puts the drafting run on **push to
main**, not on the merge request. Right now `propose` is happy to run at either
point, and running it on the MR gives the source author the advisory comment
while they can still act on it. Running it on merge gives one docs MR per
merged change rather than per opened one. Both are defensible; the choice
should be made deliberately rather than by whichever stage the code lands in.
