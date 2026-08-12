"""Configuration and credential loading.

Secrets come from the environment. A `.env` at the repository root is loaded as
a convenience for laptop runs; in CI the variables are injected by
`withCredentials` (foundation doc §8.5) and no `.env` exists.
"""

from __future__ import annotations

import os
from pathlib import Path

#: Default model for tier 2. Small on purpose: §6.3 calls for a *cheap* model
#: whose only job is a structured verdict. The resolved model name is recorded
#: in every verdict, so the logged dataset stays interpretable if this changes.
DEFAULT_MODEL = "mistral-small-latest"

DEFAULT_PROVIDER = "mistral"


def find_repo_root(start: Path | None = None) -> Path:
    """Walk up looking for a repository marker. Falls back to the cwd."""
    here = (start or Path.cwd()).resolve()
    for candidate in (here, *here.parents):
        if (candidate / ".git").exists():
            return candidate
    return here


def load_dotenv(path: Path | None = None) -> None:
    """Load `KEY=value` lines into the environment without overwriting it.

    Intentionally minimal rather than a dependency: no interpolation, no export
    syntax, no multiline values. If a `.env` ever needs more than this, the
    variable belongs in a real secret store instead.
    """
    env_path = path or (find_repo_root() / ".env")
    if not env_path.is_file():
        return
    for raw in env_path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


def api_key(provider: str) -> str | None:
    load_dotenv()
    return os.environ.get(f"{provider.upper()}_API_KEY")
