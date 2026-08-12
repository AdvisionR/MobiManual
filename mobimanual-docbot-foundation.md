# MobiManual DocBot — Project Foundation

**Status:** pre-implementation. Design agreed in outline; several inputs still missing.
**Last updated:** 2026-08-06
**Audience:** the next agent or engineer picking this up.

---

## 0. How to read this document

Every claim below is tagged:

- **[DECIDED]** — settled, do not relitigate without a reason.
- **[EVIDENCE]** — observed directly from an uploaded artifact. Trustworthy.
- **[PROPOSED]** — recommended but not yet confirmed by the team.
- **[UNKNOWN]** — genuinely open; needs an answer before dependent work starts.

If you contradict a **[DECIDED]** item, say so explicitly and explain why.

---

## 1. Goal

Build an internal R&D application ("DocBot") that watches merge/pull requests in the
MobiVisor repository and keeps the MobiVisor user manual up to date, using an LLM to
draft changes and a human to approve them.

**Non-goal:** fully autonomous publishing. A human reviewer is mandatory before any
change reaches the published manual. **[DECIDED]**

**Non-goal:** API reference documentation. That should be generated from OpenAPI specs
or source annotations, never written by a model. **[DECIDED]**

---

## 2. Product context

- Product: **MobiVisor**, a Mobile Device Management (MDM) platform. **[DECIDED]**
- Repository: internal company repository. Not public.
- Console frontend is TypeScript/React — inferred from `EnrollmentWizard.tsx`-style
  paths discussed and from E2E test artifact names. **[EVIDENCE, partial]**
- Manual language: **English only** for now. No localisation in scope. **[DECIDED]**
- Versioning: old manual versions are **archived as-is** for supporting older releases.
  No requirement to back-port doc changes into older versions. **[DECIDED]**

---

## 3. Current state of the manual

### 3.1 Format

The uploaded `combined.html` (165,947 bytes) is a **Pandoc-generated artifact**.
`<meta name="generator" content="pandoc">`, `<title>cover_page</title>`, and links to
`../seperate.css` and `../combined.css` indicate a chapter-per-file source set
concatenated at build time. **[EVIDENCE]**

**Implication: no format migration is needed.** The source is almost certainly Markdown
already. This removes what was originally assumed to be the largest cost in the project.
**[EVIDENCE]**

### 3.2 Structure (measured from the uploaded HTML)

| Element | Count |
|---|---|
| `h1` (chapters) | 15 |
| `h2` | 76 |
| `h3` | 78 |
| `h4` | 19 |
| `<p>` | 433 |
| `<li>` | 852 |
| `<table>` | 1 |
| `<code>` | 21 |
| image references | ~125 (incl. logo; many reused) |

**Interpretation:** the manual is overwhelmingly **procedural** — numbered click-paths,
not conceptual prose and not reference tables. This is the favourable case for LLM
drafting: short, formulaic, tightly coupled to UI structure.

The near-total absence of tables (1) is notable. MDM products normally carry large
policy/restriction reference tables. Either they don't exist yet, or they live outside
this document. **[UNKNOWN]** — worth checking, because generated-from-schema reference
tables are the highest-value, zero-hallucination-risk part of the plan.

### 3.3 Chapter list (as of the uploaded build)

```
1  General information about MobiVisor
2  User profile settings
3  Users
4  Roles
5  Policies
   Call blacklists / Firewall rules / Violations / Keyguard features / Kiosk modes
   Permission grant states / System update policies
   ... (Exchange, APN, single-app mode, iOS apps, passcode policies,
        shared devices, SIM card numbers, wallpapers, WiFi configs, mobile apps)
```

### 3.4 Prose register

Third-person, passive, "the user should…", with some non-native English patterns.
Example: *"Users >> Add, opens the interface which supports the logged in user to add
new user."* **[EVIDENCE]**

**Action:** extract an explicit style guide + terminology glossary from the existing
text and feed it to the drafting agent. Without it, AI-drafted sections will read as
visibly foreign against surrounding text. Estimated half a day; high return.
**[PROPOSED]**

---

## 4. Known defects in the manual — fix BEFORE the agent touches it

These will cause an agent to make plausible-looking edits in the wrong place.
**[EVIDENCE]**

1. **Chapter numbers baked into heading text** (`CHAPTER 5: POLICIES`). Inserting a
   chapter invalidates every subsequent heading, anchor, and cross-reference. Move to
   automatic numbering.
2. **Hierarchy breaks after chapter 5.** `Call Blacklists`, `Permission Grant States`
   and others sit at chapter level with no number — chapters 6+ have lost their
   container.
3. **An empty heading** produces the anchor `#section`.
4. **Duplicate headings**: `Edit Role` appears twice under `Roles`, generating duplicate
   anchors.
5. **`../seperate.css`** — misspelled path that presumably works only because a matching
   misspelling exists on disk.

---

## 5. The screenshot finding (most important discovery)

~60% of manual screenshots are **already produced by the E2E test suite**. Filenames
follow `<spec file>-<test name>.png`, a Cypress/Playwright convention. **[EVIDENCE]**

Examples:

```
settings_password_page-Should_not_save_when_current_pass_is_wrong.png
mobileapps_create_android_page-Should_add_a_new_app_from_google_play_for_android.png
roles_page-should_start_with_admin_role_only.png
users_create_page-Should_add_user_from_ldap.png
```

This inverts the original assumption that screenshots were the hardest unsolved problem.
The staleness signal is **fully deterministic**, no model required:

1. PR changes UI code.
2. E2E suite runs in CI and re-captures the screenshot.
3. Perceptual-diff the new capture against the copy in the docs repo
   (`odiff` or `pixelmatch`, small threshold — byte equality is too noisy because of
   font rendering and timing).
4. On difference, the affected manual pages are known exactly via a filename→page index.

**Phase 1 deliverable:** comment on the *source* PR — "this change alters 4 screenshots
used in chapters 3 and 7." Zero false positives.
**Phase 2:** bot commits regenerated images directly into the docs PR, since the E2E
capture is authoritative.

### 5.1 The orphan set

The remaining ~40% are hand-captured with ad-hoc names and no test behind them:
`_ldapSettings_1.png`, `_samsung_kiosk_Mode_1.png`, `_wifiConfigs_add_2.png`,
`_apn_add_form_1.png`. **[EVIDENCE]**

These need the manual registry approach (below), **or** — better — treat "manual
screenshot with no E2E test" as a backlog item. Every conversion improves both the
manual and the test suite.

Registry format for orphans only: **[PROPOSED]**

```yaml
- file: images/_ldapSettings_1.png
  renders: ["src/console/settings/LdapSettings.tsx"]
  captured: "2025-11-14"
  version: "4.2"
```

Add a CI lint that fails on any manual image with neither a test-derived name nor a
registry entry — otherwise the registry rots within two releases.

---

## 6. Architecture

### 6.1 Core principle

The manual is **plain text in version control**; HTML and PDF are build artifacts.
Already true here. **[DECIDED]**

Rationale: a model can produce a reviewable diff against text, CI can validate it, and
a human approves it in the same flow they use for code. Against a binary you get
"regenerate everything and hope."

### 6.2 Pipeline

```
Merge / PR event
  → gather context (diff, PR title/body, linked ticket, labels)
  → doc-impact gate   ── no impact ──▶ exit silently
  → agent drafts patch to docs source
  → automated validation (build, links, style lint, image existence)
  → open docs PR, linked back to the source PR
  → human review
  → merge → build HTML + PDF → publish
```

**The gate matters more than the writing.** Most merges touch tests, CI, or internals
and must produce nothing. Otherwise you generate noise, burn budget, and train
reviewers to rubber-stamp. **[DECIDED]**

### 6.3 Three-tier gate

1. **Path filter** against the doc map — pure lookup, drops most merges, costs nothing.
2. **Cheap model, structured verdict** — small model, JSON out:
   `{user_facing: bool, areas: [...], confidence: float, reason: str}`.
   **Log every verdict from day one.** After a few weeks this is a labelled dataset
   showing exactly where the gate is wrong — the real research output of phase 1.
3. **Drafting agent** — full model with file-editing tools, scoped to the docs
   directory. `human-only` and `generated` pages read-only at the filesystem level.

### 6.4 Content classification

Every manual area is tagged with one of: **[PROPOSED]**

| Class | Handling | Examples |
|---|---|---|
| `generated` | Rendered from schema at build time. No AI, no hallucination risk. | Policy/restriction tables, payload keys, error codes, permission matrices |
| `ai-drafted` | Agent drafts, human reviews. | Enrollment walkthroughs, configuration procedures, troubleshooting |
| `human-only` | Agent must never edit. | Intro, architecture overview, security statements, anything contractual |
| `no-doc-impact` | Code area explicitly excluded. | Internal plumbing (APNS/FCM transport, etc.) |

Explicit `no-doc-impact` entries matter as much as positive ones — they document *why*
the gate stays silent so nobody rediscovers it later.

### 6.5 Doc map

Hand-maintained file mapping code areas to manual sections. **Highest-leverage cheap
thing in the whole design** — deterministic retrieval beats embeddings here, and stale
entries surface as review friction rather than silent wrong edits. **[DECIDED]**

```yaml
areas:
  - id: enrollment-ios
    code: ["src/enrollment/ios/**", "src/protocol/dep/**"]
    pages: ["pages/enrollment/ios-abm.adoc"]
    class: ai-drafted
  - id: policy-schema
    code: ["schema/policies/**"]
    pages: ["pages/reference/policy-settings.adoc"]
    class: generated
  - id: push-transport
    code: ["src/protocol/apns/**", "src/protocol/fcm/**"]
    pages: []
    class: no-doc-impact
```

### 6.6 Agent behaviour rules

- Give the agent **"no change needed"** and **"needs a human — screenshot stale"** as
  first-class permitted outputs.
- Instruct it to raise uncertainty in the PR description rather than invent behaviour.
- Prefer **minimal edits** to existing sections over regenerating them.
- The drafting step must be an **agentic loop with file access and a build it must
  pass** — not one prompt returning prose. The model needs to grep for existing
  terminology, verify cross-references resolve, and iterate on build failure. **[DECIDED]**

### 6.7 Validation gates

- Docs build succeeds, failing on broken cross-references.
- Prose linter (Vale) against the extracted terminology glossary.
- Every referenced image file exists.
- No edits to `human-only` or `generated` paths.

---

## 7. Delivery model

Four options were considered. **[DECIDED]** to pursue A → B, with C worth revisiting.

- **A — advisory comment** on the source PR. No writes to docs. Days to build. Natural
  pilot; use it to learn where the gate is wrong.
- **B — bot-authored docs PR** on merge, linked back to the source PR. The destination.
- **C — ledger, batched at release.** Each merge writes a structured "doc impact record"
  to a pending queue; at release tag, one agent run processes the whole queue into a
  single coherent PR. **Worth serious consideration** — a manual is a narrative
  document, and forty independent nudges produce forty inconsistent voices. Also yields
  release notes for free. B and C combine: B detects, C writes.
- **D — auto-merge to published manual.** Rejected. The manual is customer-facing and
  arguably contractual.

Note: without a named human reviewer, B silently degrades into D. **[RISK]**

---

## 8. CI integration

### 8.1 Executor vs. detector

Jenkins is the **executor**. The merge/PR event comes from the forge. **[DECIDED]**

**[UNKNOWN] — which forge?** GitLab, Bitbucket, or GitHub Enterprise. This decides the
plugin and nothing else.

### 8.2 Plugin choice

- **Multibranch Pipeline + matching branch source plugin** (GitLab / Bitbucket / GitHub
  Branch Source) is the default. Auto-discovers MRs as `PR-123` jobs and exposes
  `CHANGE_ID`, `CHANGE_TARGET`, `CHANGE_BRANCH`, `CHANGE_TITLE`, `CHANGE_AUTHOR`,
  `CHANGE_URL`. **[PROPOSED]**
- **Generic Webhook Trigger plugin** only if you need fields branch source doesn't
  expose — MR labels and linked issue are the usual reasons, and both matter to the gate.
- **Recommended hybrid:** branch source for discovery, plus direct forge API calls from
  DocBot for labels and linked tickets. Simpler than maintaining JSONPath bindings.

### 8.3 Two triggers, not one

| Trigger | Action |
|---|---|
| MR opened/updated | Gate verdict + screenshot warnings, posted as a comment on that MR |
| Push to main | Drafting run that opens the docs PR |

### 8.4 Diff computation gotcha

Multibranch often does a shallow clone, and PR jobs may check out a merge commit rather
than the branch head. **Disable shallow clone in the checkout behaviours**, or
`merge-base` silently fails.

```groovy
sh '''
  git fetch --no-tags --depth=0 origin +refs/heads/${CHANGE_TARGET}:refs/remotes/origin/${CHANGE_TARGET}
  git diff --name-only $(git merge-base HEAD origin/${CHANGE_TARGET})...HEAD > changed_files.txt
'''
```

### 8.5 Keep Jenkins thin

**No logic in Groovy.** The `Jenkinsfile` collects context, runs a container, publishes
artifacts. Everything else lives in a standalone CLI that runs identically on a laptop.
**[DECIDED]**

```groovy
pipeline {
  agent { docker { image 'registry.internal/docbot:1.4.2' } }
  stages {
    stage('Doc impact') {
      when { changeRequest() }
      steps {
        withCredentials([string(credentialsId: 'llm-api-key',    variable: 'LLM_API_KEY'),
                         string(credentialsId: 'forge-bot-token', variable: 'FORGE_TOKEN')]) {
          sh 'docbot gate --changed-files changed_files.txt --mr $CHANGE_ID --out verdict.json'
          sh 'docbot screenshots --changed-files changed_files.txt --comment --mr $CHANGE_ID'
        }
      }
    }
  }
  post { always { archiveArtifacts 'verdict.json' } }
}
```

Pin DocBot as a **versioned container image** — it needs Pandoc, a model SDK, and a docs
build at fixed versions, and Jenkins agents drift. Move the wrapper into a Jenkins Shared
Library once a second repo needs it.

### 8.6 CLI shape

Composable subcommands, each independently testable, each emitting a JSON artifact:

```
docbot gate              # is this user-facing? which areas?
docbot screenshots       # which images changed / are stale?
docbot render-reference  # schema → generated tables
docbot draft             # agentic docs edit
docbot validate          # build + lint + link check
```

This also gives the evaluation harness for free: replay a corpus of historical MRs
through `gate` offline and score verdicts without touching Jenkins.

---

## 9. Implementation language

**Python**, with one dependency. **[PROPOSED]**

Reasons: mature model SDKs and agent tooling; Python-native documentation ecosystem
(Pandoc wrappers, `python-frontmatter`, PyYAML); Jinja2 for rendering generated
reference tables; fast edit-run loop, which prompt work rewards. `click`/`typer` for CLI,
`pytest` for the eval harness.

**The dependency — [UNKNOWN]: where do the policy/restriction schemas live?**

- If they are backend-side or already JSON Schema → **Python**, no complications.
- If they are TypeScript types or Zod schemas → parsing them from Python is miserable.
  Two clean options: write DocBot in **TypeScript**, or **export JSON Schema as a build
  step in the console repo** and stay in Python.

**Recommendation:** the JSON Schema export regardless. It is a useful artifact in its own
right, decouples docs from console internals, and means a console refactor doesn't break
the manual.

Go is defensible if single-binary distribution matters, but the doc-tooling gap and
slower iteration make it a poor fit for the research phase.

Note: the screenshot filename→page index is pure string parsing and is language-agnostic.

---

## 10. Model provider

Either **OpenAI or Anthropic**; both work. **[DECIDED]**

Keep the provider behind a thin interface so they can be A/B tested. For an R&D project,
comparative quality data on the same corpus is a legitimate deliverable in itself.

**Governance — must be resolved before the pilot:** diffs from a proprietary MDM codebase
will leave the network. Both vendors offer zero-retention and EU-region arrangements.
Get this agreed **in writing** first, not after. **[RISK / OPEN]**

---

## 11. Phasing

### Phase 1 — no AI at all

1. Obtain the Markdown sources + build script (see §12).
2. Fix the heading hierarchy defects (§4) and switch to automatic chapter numbering.
3. Build the image→page index by parsing `combined.html`.
4. Wire the E2E screenshot perceptual-diff into a source-PR comment.
5. Extract the style guide + terminology glossary from existing prose.
6. Build `generated` reference tables from policy schemas, if such schemas exist.

Phase 1 delivers real value on its own and makes the doc-impact PR template an easier
sell to the team.

### Phase 2 — gate in advisory mode

Deploy the gate commenting on source PRs. Collect verdict data. Tune. No writes to docs.

### Phase 3 — drafting agent

Turn on `draft` against docs PRs, starting with **low-risk areas** (troubleshooting)
before opening it to enrollment procedures.

---

## 12. Open questions

| # | Question | Blocks | Owner |
|---|---|---|---|
| 1 | Which forge — GitLab / Bitbucket / GitHub Enterprise? | Jenkins plugin choice | team |
| 2 | Are policy/restriction schemas TypeScript or backend-side? | Python vs TS decision | team |
| 3 | Can we get the Markdown sources + build script for the manual? | Everything | user (in progress) |
| 4 | Does the PDF build share the same source, or has it diverged? | Build pipeline design | user (PDF pending) |
| 5 | Who is the named human reviewer for docs PRs? Is there a technical writer? | Option B viability | team |
| 6 | What is the contract for "user-facing"? Labels, conventional commits, or a mandatory "Doc impact" section in the PR template? | Gate design | team — *under discussion* |
| 7 | Do policy/restriction reference tables exist anywhere? (only 1 table in the manual) | `generated` class scope | team |
| 8 | Data-governance sign-off for sending code diffs to an external model API | Pilot start | legal/security |

---

## 13. Artifacts referenced

- `combined.html` — 165,947 bytes, Pandoc output, the whole manual concatenated.
  Uploaded and analysed. **The analysis in §3–§5 derives entirely from this file.**
- A PDF with images — mentioned by the user, **not yet provided**.
- Markdown sources — **not yet provided**, existence inferred from Pandoc metadata.

---

## 14. Standing principles

1. Human review is mandatory. Never ship option D.
2. Deterministic beats probabilistic. Prefer schema rendering, filename parsing, and
   path lookups over asking a model. Use the model only where prose judgement is
   genuinely required.
3. The gate's job is mostly to say nothing.
4. Log every verdict and every draft. This is an R&D project; the data is the output.
5. Fix the document's structure before letting an agent edit it.
