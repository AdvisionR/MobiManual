# mobivisor-console (fixture)

Not the real MobiVisor. A throwaway repository that merge requests can be
opened against, shaped like the real one everywhere DocBot depends on the
shape. `scripts/seed-project.sh` pushes it to GitLab.

```
gruntfile.js                     htmlDocPages — the order of the manual
package.json                     Grunt and Protractor, the documentation toolchain
doc-map.json                     code area -> manual pages
scripts/check-missing-doc.js     routes vs pages, pages vs htmlDocPages, language parity
Jenkinsfile                      runs docbot once a merge request has landed on main
tools/docbot/                    DocBot itself: a Python CLI the Jenkinsfile installs and runs

public/app/                      AngularJS console
  routes.js                        the route table documentation filenames derive from
  users/  devices/  reports/
  enrollment/ios/
  policies/kiosk/  policies/restrictions/
public/doc/<lang>/               the manual, one folder per language: en, tr, de
  _<route>.md                      one page per console route
  cover_page.md  chapter1.md       pages with no route behind them
  search.md  break.md              build machinery, not content
  screenshots/                     captured by the E2E suite
  img/                             everything else
server/protocol/apns/            backend plumbing, no user-visible surface
schema/policies/                 restriction schema the reference page is generated from
e2e/                             Protractor suite and the screenshot helpers
doc-impact/pending/              the ledger DocBot writes into
```

## Documentation filenames come from routes

A console route determines the name of its manual page. Slashes become
underscores and parameters collapse to `id`:

```
#!/devices           ->  _devices.md
#!/devices/:id       ->  _devices_id.md
#!/policies/kiosk    ->  _policies_kiosk.md
```

This makes most of the code-to-docs mapping a lookup rather than a
hand-maintained list. `doc-map.json` covers only what the convention cannot
reach: backend areas, the schema-generated page, pages with no route, and the
exclusions.

## Adding a page is two steps

A Markdown file that is not listed in `htmlDocPages` in `gruntfile.js` exists on
disk but appears in neither `combined.html` nor the PDF. Creating the file is
the first step; registering it is the second, and it is the one that gets
forgotten. Anything DocBot writes has to do both.

## Screenshots

Two independent mechanisms write into `public/doc/<lang>/screenshots/`, and
both are driven by tests:

| Produced by | Named after | Example |
|---|---|---|
| `helper.screenshot()` with no argument | the current route | `_devices_1.png` |
| `helper.screenshot('kiosk_mode')` / `docshot()` | the given name | `_kiosk_mode_1.png` |
| `protractor-screenshot-reporter` | the Jasmine description | `devices_page-should_list_enrolled_devices.png` |

Images that no test produces live in `img/` instead. The directory is the
boundary: a file under `screenshots/` can be regenerated, a file under `img/`
cannot.

Every language has its own capture set, so one UI change invalidates the same
screenshot three times.

## What the gate should do with a merge here

Each row is a merge request you can open and a prediction to check the gate
against. `scripts/open-test-mr.sh` takes the row name as its argument.

| Touch this | Doc-map area | Class | Expected gate behaviour |
|---|---|---|---|
| `public/app/enrollment/ios/**` | `enrollment-ios` | `ai-drafted` | flag doc impact, propose `_enrollment_ios.md` |
| `public/app/policies/kiosk/**` | `kiosk-modes` | `ai-drafted` | flag doc impact, and the screenshot as possibly stale |
| `public/app/users/**` | `users` | `ai-drafted` | flag doc impact |
| `schema/policies/**` | `policy-schema` | `generated` | flag for regeneration, never a drafted edit |
| `server/protocol/apns/**` | `push-transport` | `no-doc-impact` | stay silent |
| `Jenkinsfile`, `e2e/**` | `ci-and-tests` | `no-doc-impact` | stay silent |
| `public/doc/**` alone | `manual-source` | `no-doc-impact` | stay silent — the manual is the output |
| `tools/docbot/**` | `docbot` | `no-doc-impact` | stay silent — changing the bot does not change the product |
| `public/app/reports/**` | none | — | tier 1 cannot answer; it goes to the model, and the verdict is logged |

Proving silence matters as much as proving detection: most merges touch tests,
CI or internals and must produce nothing.

Nothing reads `doc-map.json` yet. For every merge that reaches `main`, `docbot`
opens a placeholder docs merge request (see `tools/docbot/README.md`). The path
filter is the next thing to build, and this table is its specification.

## Known findings

`node scripts/check-missing-doc.js` exits non-zero here, reporting two things
that are deliberate:

- `#!/reports/export` has no documentation page — the unmapped case the gate
  has to hand to the model.
- `_policies_kiosk.md` is missing from `de/` — the translation gap a language
  parity check has to catch.

## What is deliberately missing

No running console, so `grunt screenshot_*` cannot capture anything and
`grunt web_docs` only reports what it would build. The images under
`public/doc/` are placeholders of the right names and dimensions. Archived
manual versions are a release concern and are not modelled.
