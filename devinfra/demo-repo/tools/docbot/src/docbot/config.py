"""Deployment settings. The only module that reads the environment.

Everything here would differ between two deployments of DocBot, so it comes
from the executor rather than from the repository DocBot watches.
"""

import os
from dataclasses import dataclass


class ConfigError(Exception):
    """A required setting is missing. Raised before any network call."""


@dataclass(frozen=True)
class Config:
    gitlab_url: str
    project: str
    token: str


_VARIABLES = {
    "gitlab_url": "DOCBOT_GITLAB_URL",
    "project": "DOCBOT_PROJECT",
    "token": "DOCBOT_GITLAB_TOKEN",
}


def load(environ=os.environ) -> Config:
    missing = [name for name in _VARIABLES.values() if not environ.get(name)]
    if missing:
        raise ConfigError("missing setting: " + ", ".join(missing))
    return Config(**{field: environ[name] for field, name in _VARIABLES.items()})
