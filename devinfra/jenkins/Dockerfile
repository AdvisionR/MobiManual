ARG JENKINS_BASE_VERSION=lts-jdk21
FROM jenkins/jenkins:${JENKINS_BASE_VERSION}

# python3 and python3-venv run DocBot. Nothing of DocBot itself is baked in:
# the Jenkinsfile installs it from the checkout (tools/docbot/) into a venv in
# the workspace, which is how it will reach the real Jenkins too. pandoc builds
# the manual and node runs the completeness check, so the validation gates can
# be exercised in the same container as the bot. scripts/status.sh uses curl.
USER root
RUN apt-get update \
    && apt-get install -y --no-install-recommends curl ca-certificates pandoc nodejs \
       python3 python3-venv \
    && rm -rf /var/lib/apt/lists/*
USER jenkins

# Plugins are baked into the image rather than installed at runtime, so the
# jenkins-home volume stays disposable: delete all Jenkins state and an
# identically-configured controller comes back.
COPY plugins.txt /usr/share/jenkins/ref/plugins.txt
RUN jenkins-plugin-cli --plugins -f /usr/share/jenkins/ref/plugins.txt

COPY casc/ /var/jenkins_conf/
