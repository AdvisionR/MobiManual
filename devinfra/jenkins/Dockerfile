ARG JENKINS_BASE_VERSION=lts-jdk21
FROM jenkins/jenkins:${JENKINS_BASE_VERSION}

# jq and curl are what the docbot stub is written against. pandoc builds the
# manual and node runs the completeness check, so the validation gates can be
# exercised in the same container as the bot.
USER root
RUN apt-get update \
    && apt-get install -y --no-install-recommends jq curl ca-certificates pandoc nodejs \
    && rm -rf /var/lib/apt/lists/*
USER jenkins

# Plugins are baked into the image rather than installed at runtime, so the
# jenkins-home volume stays disposable: delete all Jenkins state and an
# identically-configured controller comes back.
COPY plugins.txt /usr/share/jenkins/ref/plugins.txt
RUN jenkins-plugin-cli --plugins -f /usr/share/jenkins/ref/plugins.txt

COPY casc/ /var/jenkins_conf/

# The bot. Rebuild the image after editing it:  docker compose up -d --build jenkins
COPY --chmod=755 docbot /usr/local/bin/docbot
