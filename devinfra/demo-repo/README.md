# mobivisor (fixture monorepo)

Not the real MobiVisor. A throwaway repository that exists so merge requests
can be opened against something — and, since it carries the manual as well as
the console code, so those merge requests can touch **code, docs, or both**.

This directory is pushed to GitLab by `scripts/seed-project.sh`.

```
doc-map.json                     code area -> manual pages. The contract between the halves.
Jenkinsfile                      runs docbot once a merge request has landed on main
src/                             the code half
  enrollment/ios/                area: enrollment-ios      class: ai-drafted
  console/kiosk/                 area: kiosk-modes         class: ai-drafted
  console/settings/              area: users-and-roles     class: ai-drafted
  protocol/apns/                 area: push-transport      class: no-doc-impact
schema/policies/                 area: policy-schema       class: generated
tests/                           area: ci-and-tests        class: no-doc-impact
docs/                            the docs half — see docs/README.md
  manual.yaml                    chapter order
  pages/                         one Markdown file per manual section
  images/registry.yaml           orphan-screenshot registry
  doc-impact/pending/            the ledger DocBot writes into
```

## Why one repository

The alternative — a `mobivisor-console` repo and a `mobivisor-manual` repo — is
what this fixture replaced. Both shapes are plausible for the real product, and
the fixture picks one so the awkward parts are visible rather than theoretical:

- **A code change and its documentation can land in one merge request.** That
  is the case a two-repo setup cannot express at all, and it is the outcome
  DocBot should be steering reviewers toward.
- **DocBot's output lands on the branch that triggers DocBot.** In two repos
  the loop is impossible by construction; here it has to be cut deliberately.
  It is cut twice — see `manual-source` in `doc-map.json`.
- **One path convention has to span both halves.** Anything that crosses the
  boundary (`doc-map.json`, `docs/images/registry.yaml`) is repo-root-relative.
  Anything purely inside the docs (`docs/manual.yaml`, the image links in the
  Markdown) stays relative to `docs/`.

## What the gate should do with a merge here

The table is the fixture's whole purpose: each row is a merge request you can
open, and a prediction to check the gate against.

Nothing reads `doc-map.json` yet — `docbot` currently reports every merge that
reaches `main`, and the tier-1 path filter of foundation doc §6.3 is the next
thing to build. Until it exists, the table is the specification for it and the
fixture is the test set.

| Touch this | Doc-map area | Class | Expected gate behaviour |
|---|---|---|---|
| `src/enrollment/ios/**` | `enrollment-ios` | `ai-drafted` | flag doc impact, propose `docs/pages/enrollment/ios-abm.md` |
| `src/console/kiosk/**` | `kiosk-modes` | `ai-drafted` | flag doc impact, and the screenshot as possibly stale |
| `src/console/settings/Ldap*` | `users-and-roles` | `ai-drafted` | flag doc impact on two pages |
| `schema/policies/**` | `policy-schema` | `generated` | flag, but for **regeneration** — never a drafted edit |
| `src/protocol/apns/**` | `push-transport` | `no-doc-impact` | stay silent |
| `Jenkinsfile`, `tests/**` | `ci-and-tests` | `no-doc-impact` | stay silent |
| `docs/**` alone | `manual-source` | `no-doc-impact` | stay silent — the manual is the output |
| a path in no area | — | — | **the interesting one.** Tier 1 cannot answer; it goes to the tier-2 model, and the verdict gets logged |

`scripts/open-test-mr.sh` takes the row you want as its argument.

Proving silence matters as much as proving detection: foundation doc §6.2 —
*"Most merges touch tests, CI, or internals and must produce nothing."*

## What is deliberately missing

No build, no images, no package manifest, no CI beyond the `Jenkinsfile`. The
fixture is shaped like the real thing only where DocBot depends on the shape.
