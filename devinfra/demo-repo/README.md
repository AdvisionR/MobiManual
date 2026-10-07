# mobivisor-console (fixture)

Not the real MobiVisor. A throwaway repository that merge requests can be
opened against, shaped like the real one everywhere DocBot depends on the
shape. `scripts/seed-project.sh` pushes it to GitLab.

```
gruntfile.js                     htmlDocPages — the order of the manual
package.json                     AngularJS, Grunt and Protractor
doc-map.json                     paths whose changes never need a manual update
scripts/check-missing-doc.js     routes vs pages, pages vs htmlDocPages, language parity
scripts/render-restrictions.js   the generated table on _policies_restrictions.md
Jenkinsfile                      runs docbot once a merge request has landed on main
tools/docbot/                    DocBot itself: a Python CLI the Jenkinsfile installs and runs

public/index.html                the console shell: top bar, menu, language, Help link
public/login.html                the sign-in page, outside the console app
public/i18n/{en,tr,de}.json      every UI label; templates hold keys, never text
public/app/
  app.js  routes.js  help.js       module, route table, Help link
  features.js                      feature flags: a finished feature ships dark until its flag is on
  services/                        one $http wrapper per API area
  <area>/                          a controller and its template per route
public/doc/<lang>/               the manual, one folder per language: en, tr, de
  _<route>.md                      one page per console route
  cover_page.md  chapter1.md       pages with no route behind them
  search.md  break.md              build machinery, not content
  screenshots/                     captured by the E2E suite
  img/                             everything else
server/                          the backend rules the manual states, and plumbing it does not
schema/policies/                 restriction schema the reference table is generated from
e2e/                             Protractor suite and the screenshot helpers
doc-impact/pending/              the ledger of an earlier design; DocBot no longer writes here
```

## The console

Seventeen routes, each with a controller and a template: Dashboard, Users,
Groups, Devices and a device's detail page, Device Commands, Android and iOS
enrollment, Policies with its Passcode, Kiosk and Restrictions pages, Access
Point Names, App Installations, Audit Log, Settings, and a scheduled report
export. Every route but the export has a manual page.

Labels live in `public/i18n/<lang>.json`, so a template says
`{{ 'DEVICES.ACTION_RETIRE' | translate }}` and only `en.json` says **Retire**.
A merge request that renames a button changes a locale file and no template.
To learn what a field is called, DocBot has to follow the key into `en.json`.

`server/` holds the rules behind the manual's numbers and the plumbing behind
none of them:

| Module | What the manual says because of it |
|---|---|
| `auth/password-policy.js` | passwords of at least 8 characters with a letter and a digit; lockout after 5 attempts for 15 minutes |
| `auth/session.js` | signed out after 30 minutes; 5 to 120 under Settings |
| `auth/permissions.js` | the Roles table; who may send which command |
| `auth/invitation.js` | password links valid for 48 hours |
| `commands/definitions.js` | which commands run where; Ring lasts 2 minutes |
| `commands/command-queue.js` | unacknowledged commands expire after 24 hours |
| `protocol/android/checkin.js` | Android devices check in every 15 minutes |
| `enrollment/android-tokens.js` | QR codes and tokens valid for 7 days |
| `apps/install-retry.js` | failed installations retried 3 times, an hour apart |
| `audit/retention.js` | audit entries kept for 365 days |
| `dashboard/summary.js` | what the tiles count |
| `devices/query.js` | what the device list's filters do |
| `policies/` | passcode limits, kiosk modes, one policy per type per group, APN entries |
| `protocol/apns/`, `logging/`, `db/migrations/` | nothing: plumbing no reader of the manual sees |

## Facts the manual states more than once

A change to one of these makes several pages wrong at once. Drafting has to
find all of them, which the table of contents alone does not show:

| Fact | Pages |
|---|---|
| Commands expire after 24 hours | `_devices_id.md`, `_devicescommands.md` |
| **Retire**, retired | `_devices.md`, `_devices_id.md`, `_devicescommands.md`, `_dashboard.md`, `_users.md` |
| Passwords of at least 8 characters | `chapter1.md`, `_users.md` |
| Session timeout of 30 minutes | `chapter1.md`, `_settings.md` |
| Who may send which command | `_users.md`, `_devicescommands.md` |
| The Apple Push certificate | `_settings.md`, `_dashboard.md`, `_enrollment_ios.md`, `_devicescommands.md` |

And words that mean different things on different pages, so that the page a
change names is not always the page it affects:

| Word | Means |
|---|---|
| passcode | the device passcode (`_policies_passcode.md`, `_policies_kiosk.md`, **Clear passcode**), never the console password (`chapter1.md`, `_users.md`) |
| APN / APNs | Access Point Names, the cellular settings (`_apns.md`); `server/protocol/apns/` is Apple Push, and the Apple Push certificate is on `_settings.md` |
| compliance | a device state (`_policies.md`), shown on `_devices.md`, `_devices_id.md` and `_dashboard.md` |
| department | an attribute from the directory (`_devices_id.md`), not a group (`_groups.md`) |

## What is modelled on the real MobiVisor, and what is invented

The foundation doc records a fixture detail once read back as evidence about
the real repository. So, explicitly:

- **From the description of the real documentation system:** `public/doc/<lang>/`,
  the route-to-filename rule, `htmlDocPages`, `search.md` and `break.md`, the two
  screenshot mechanisms and `img/`, `check-missing-doc`, the AngularJS hashbang
  routes, and the page and image names `_users.md`, `_devices.md`, `_groups.md`,
  `_policies.md`, `_devicescommands.md`, `_apns.md`, `_appinstallations.md`,
  `_apn_add_form_1.png` and `commands_for_ios_devices.png`.
- **Invented here:** everything else. In particular the i18n files and
  angular-translate, `server/` and its layout, the roles, every number the manual
  states, what `_apns.md` is about (read here as Access Point Names, from
  `_apn_add_form_1.png`), the Help link's mechanics, and the restriction schema
  with its generator.

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
of contents (`htmlDocPages`, with each page's headings) and decides which pages
the change affects, if any. This naming convention is what makes those file
names meaningful to it.

## Adding a page is two steps

A Markdown file that is not listed in `htmlDocPages` in `gruntfile.js` exists on
disk but appears in neither `combined.html` nor the PDF. Creating the file is
the first step; registering it is the second, and it is the one that gets
forgotten. Anything DocBot writes has to do both.

## A generated page

The settings table on `_policies_restrictions.md` is rendered from
`schema/policies/android-restrictions.json` by `scripts/render-restrictions.js`
(`grunt render-restrictions`), in all three languages, between two marker
comments. The rest of the page is written by hand. `--check` exits non-zero when
a table is stale.

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
and must produce nothing. Proving that DocBot drafts the right edit, and stays
silent for the right reason, takes merge requests with real changes. Those are
the scenarios in `devinfra/scenarios/` of the MobiManual repository, which
`open-test-mr.sh` applies the same way.

DocBot reads `doc-map.json` at the merge commit and drops the ignored files
before any model sees the merge request. If nothing is left, it stops there.
Otherwise triage decides whether the change affects the manual, and drafting
finds the pages and edits them (see `tools/docbot/README.md`).

## Known findings

`node scripts/check-missing-doc.js` exits non-zero here, reporting two things
that are deliberate:

- `#!/reports/export` has no documentation page — the unmapped case the gate
  has to hand to the model.
- `_policies_kiosk.md` is missing from `de/` — the translation gap a language
  parity check has to catch.

The base fixture also has one bug on purpose: the dashboard's Devices tile
counts retired devices, although `_dashboard.md` and the tile's own hint say it
does not. The `dashboard-count-fix` scenario fixes it.

## What is deliberately missing

No running console, so `grunt screenshot_*` cannot capture anything and
`grunt web_docs` only reports what it would build. There is no `public/lib/`,
no stylesheet and no `server/api/`: the controllers and services show what the
console does, not how it is served. The images under `public/doc/` are
placeholders of the right names and dimensions. Archived manual versions are a
release concern and are not modelled.
