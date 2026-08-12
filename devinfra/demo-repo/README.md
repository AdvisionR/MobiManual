# mobivisor-console (fixture)

Not the real MobiVisor console. This is a throwaway repository used to exercise
the DocBot prototype end to end: it exists so merge requests can be opened
against paths that the doc map classifies differently.

| Path | Doc-map area | Class | Expected gate behaviour |
|---|---|---|---|
| `src/enrollment/ios/**` | `enrollment-ios` | `ai-drafted` | flag doc impact |
| `src/protocol/apns/**` | `push-transport` | `no-doc-impact` | stay silent |
| `Jenkinsfile`, `tests/**` | `ci-and-tests` | `no-doc-impact` | stay silent |

`Jenkinsfile` is the Phase 1 prototype: it detects the merge request, pulls the
changed-file list from the GitLab API, applies the tier-1 path filter, and
archives `verdict.json`.
