"""Verdict logging — foundation doc §14.4.

"Log every verdict and every draft. This is an R&D project; the data is the
output." §6.3 is more specific: after a few weeks the log is a labelled dataset
showing exactly where the gate is wrong, which is the real deliverable of
phase 1.

Append-only JSONL, one verdict per line, so a run can never corrupt earlier
records and the file streams into anything.
"""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

DEFAULT_LOG_DIR = Path(".docbot")
LOG_NAME = "verdicts.jsonl"

#: "Log every verdict *and every draft*." A proposal is the first thing DocBot
#: writes to another repository, so it gets its own stream rather than being
#: mixed into the verdict dataset the gate's evaluation depends on.
PROPOSAL_LOG_NAME = "proposals.jsonl"


def append(verdict: dict[str, Any], log_dir: str | Path | None = None, name: str = LOG_NAME) -> Path:
    directory = Path(log_dir or os.environ.get("DOCBOT_LOG_DIR") or DEFAULT_LOG_DIR)
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / name
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(verdict, sort_keys=True) + "\n")
    return path


def read(log_dir: str | Path | None = None, name: str = LOG_NAME) -> list[dict[str, Any]]:
    path = Path(log_dir or DEFAULT_LOG_DIR) / name
    if not path.is_file():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")
