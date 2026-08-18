# mobivisor-console (fixture)

Not the real MobiVisor console — a throwaway repository that exists so merge
requests can be opened against something.

`Jenkinsfile` is the whole integration on this side: when Jenkins builds a
merge request, it runs `docbot`. The bot itself lives in the Jenkins image
(`devinfra/jenkins/docbot`), not here, because it watches this repository
rather than belonging to it.

This directory is pushed to GitLab by `scripts/seed-project.sh`.
