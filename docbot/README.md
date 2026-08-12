# DocBot CLI

The standalone command line behind MobiManual DocBot. Foundation doc §8.5 is the
governing constraint: **no logic in Groovy**. Jenkins collects context, runs one
of these subcommands, and archives the JSON it produces. Everything here runs
identically on a laptop.

Implements Phase 1 and Phase 2 of §11 — the deterministic screenshot work and
the doc-impact gate. No drafting agent; that is Phase 3.

---

## 1. Quick start

```bash
uv sync
uv run pytest                                    # 43 tests, no network

# deterministic, no model, no spend
uv run docbot screenshots index --manual ../combined.html --out .docbot/image-index.json
uv run docbot screenshots audit --index .docbot/image-index.json

# the gate
echo "src/enrollment/ios/EnrollmentWizard.tsx" > changed.txt
uv run docbot gate --changed-files changed.txt --doc-map examples/doc-map.yaml \
  --title "Update iOS enrollment wizard copy"
```

`MISTRAL_API_KEY` comes from `.env` at the repository root, or the environment.
`--no-model` runs tier 1 alone and never touches the network.

---

## 2. Commands

| Command | Does | Model? |
|---|---|---|
| `gate` | Is this MR user-facing? Which manual areas? | tier 2 only |
| `screenshots index` | Build the image→page index from the built manual | no |
| `screenshots impact` | Which pages does this MR put in question? | no |
| `screenshots audit` | Lint: orphans without registry entries, missing files | no |
| `eval` | Replay a labelled corpus, score the gate | optional |

Named in §8.6 and **not** built: `render-reference` (needs the policy schemas —
open question #7), `draft` (Phase 3), `validate` (needs the Markdown sources —
open question #3).

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

## 4. Screenshots

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

## 5. Evaluation

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

## 6. Divergence from the foundation doc

**§10 says "Either OpenAI or Anthropic; both work. [DECIDED]". This uses
Mistral**, at the user's direction, because that is the API key available. The
doc asks that contradictions of a [DECIDED] item be stated explicitly, so:
stated. Nothing about the design depends on it — `providers/` is a one-method
interface and a second vendor is a new file (`providers/mistral.py` is 90 lines).
The §10 requirement that actually matters, keeping the provider swappable for
A/B comparison on the same corpus, is satisfied.

Two other notes:

- **§9 proposed Python.** Followed. The open dependency question (where the
  policy schemas live) is untouched — `render-reference` is not built.
- **The doc map is YAML** per §6.5. The loader also reads JSON, so the Jenkins
  prototype's existing `demo-repo/docs/doc-map.json` works unchanged and the
  eventual wiring is a one-line swap rather than a migration.

---

## 7. Layout

```
src/docbot/
  cli.py           click entry point, one function per subcommand
  gate.py          tier orchestration, prompt, decision rules
  docmap.py        doc map loading + validation, tier 1
  screenshots.py   filename convention, index, impact, audit
  manual.py        HTML parsing of the built manual
  evalharness.py   corpus replay and scoring
  verdictlog.py    append-only JSONL
  providers/       one-method interface: mistral, fake
examples/doc-map.yaml
tests/             43 tests, all offline
```

`providers/fake.py` is a deterministic keyword stub. It is not good, and is not
meant to be — its value is that it is *stable*, so a failing test means the
pipeline broke rather than the model drifted.

---

## 8. Not wired into Jenkins yet

The `Jenkinsfile` in `devinfra/demo-repo/` still runs the jq placeholder. Wiring
is a three-step change: install docbot into the Jenkins image, swap the jq block
for `docbot gate`, add `MISTRAL_API_KEY` as a Jenkins credential. Note that
rebuilding that image re-resolves all plugins, which are unpinned — see
`devinfra/README.md` §7.
