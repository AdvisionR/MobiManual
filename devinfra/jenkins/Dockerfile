ARG JENKINS_BASE_VERSION=lts-jdk21
FROM jenkins/jenkins:${JENKINS_BASE_VERSION}

# Plugins are baked into the image rather than installed at runtime. This keeps
# the jenkins-home volume disposable: you can delete all Jenkins state and get
# an identically-configured controller back, which is the whole point of the
# "clean teardown" requirement.
USER root
RUN apt-get update \
    && apt-get install -y --no-install-recommends jq curl ca-certificates \
    && rm -rf /var/lib/apt/lists/*
USER jenkins

COPY plugins.txt /usr/share/jenkins/ref/plugins.txt
RUN jenkins-plugin-cli --plugins -f /usr/share/jenkins/ref/plugins.txt

COPY casc/ /var/jenkins_conf/
