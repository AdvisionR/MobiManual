# mobivisor-console (fixture)

Not the real MobiVisor. A throwaway repository that merge requests can be
opened against, shaped like the real one everywhere DocBot depends on the
shape. `scripts/seed-project.sh` pushes it to GitLab.

```
gruntfile.js                     htmlDocPages — the order of the manual
package.json                     Grunt and Protractor, the documentation toolchain
doc-map.json                     paths whose changes never need a manual update
scripts/check-missing-doc.js     routes vs pages, pages vs htmlDocPages, language parity
Jenkinsfile                      runs docbot once a merge request has landed on main
tools/docbot/                    DocBot itself: a Python CLI the Jenkinsfile installs and runs

public/app/                      AngularJS console
  routes.js                        the route table documentation filenames derive from
  features.js                      feature flags: a finished feature ships dark until its flag is on
  users/  devices/  reports/       users/ also has its template, users.html
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

DocBot does not map code to pages by hand. `doc-map.json` lists only the paths
whose changes never need a manual update: tests, CI, DocBot itself and the
manual. For everything else, a model reads the diff next to the manual's table
of contents (`htmlDocPages`, with each page's headings) and names the pages the
change affects, if any. This naming convention is what makes those file names
meaningful to it.

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

## What DocBot should do with a merge here

Each row is a merge request you can open. `scripts/open-test-mr.sh` takes the
kind as its argument.

| Kind | Touches | `doc-map.json` | Then |
|---|---|---|---|
| `ci` | `e2e/**` | ignored (`ci-and-tests`) | nothing, not even a model call |
| `docs` | `public/doc/**` alone | ignored (`manual-source`) | nothing: the manual is the output |
| — | `tools/docbot/**` | ignored (`docbot`) | nothing: changing the bot does not change the product |
| `code`, `kiosk`, `users`, `devices` | a console controller | — | goes to the model |
| `schema` | `schema/policies/**` | — | goes to the model |
| `internal` | `server/protocol/apns/**` | — | goes to the model, which should find no page |
| `unmapped` | `public/app/reports/**`, which has no page | — | goes to the model, which should find no page and say so |
| `both` | a controller and its own page | the page change is ignored as a trigger | the model is told the page was already edited in this merge request |

These kinds only append a comment to each file, so the right answer from the
model is "no page needs changing" every time. That proves silence, which
matters as much as proving detection: most merges touch tests, CI or internals
and must produce nothing. Proving that DocBot drafts the right edit takes merge
requests with real behaviour changes. Those are the scenarios in
`devinfra/scenarios/` of the MobiManual repository, which `open-test-mr.sh`
applies the same way.

DocBot reads `doc-map.json` at the merge commit and drops the ignored files
before any model sees the merge request. If nothing is left, it stops there.
Otherwise triage names the affected pages, or none, and drafting edits them (see
`tools/docbot/README.md`).

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
