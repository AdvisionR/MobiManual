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


@dataclass(frozen=True)
class LLMConfig:
    api_key: str
    model: str


_VARIABLES = {
    "gitlab_url": "DOCBOT_GITLAB_URL",
    "project": "DOCBOT_PROJECT",
    "token": "DOCBOT_GITLAB_TOKEN",
}

# Mistral is the only provider so far; DOCBOT_LLM_PROVIDER comes with the second.
_LLM_VARIABLES = {
    "api_key": "MISTRAL_API_KEY",
    "model": "DOCBOT_LLM_MODEL",
}


def load(environ=os.environ) -> Config:
    return Config(**_read(_VARIABLES, environ))


def load_llm(environ=os.environ) -> LLMConfig:
    return LLMConfig(**_read(_LLM_VARIABLES, environ))


def _read(variables: dict[str, str], environ) -> dict[str, str]:
    missing = [name for name in variables.values() if not environ.get(name)]
    if missing:
        raise ConfigError("missing setting: " + ", ".join(missing))
    return {field: environ[name] for field, name in variables.items()}
