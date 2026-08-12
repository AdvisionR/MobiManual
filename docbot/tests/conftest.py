from __future__ import annotations

from pathlib import Path

import pytest

from docbot import docmap

FIXTURES = Path(__file__).parent / "fixtures"
EXAMPLES = Path(__file__).parents[1] / "examples"


@pytest.fixture
def doc_map() -> docmap.DocMap:
    """The shipped example map. Tests run against the real thing on purpose —
    a broken example map should fail the suite."""
    return docmap.load(EXAMPLES / "doc-map.yaml")


@pytest.fixture
def mini_manual() -> Path:
    return FIXTURES / "mini-manual.html"


@pytest.fixture
def corpus_path() -> Path:
    return FIXTURES / "corpus.jsonl"
