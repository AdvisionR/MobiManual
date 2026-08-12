"""Model providers behind a thin interface.

Foundation doc §10: either OpenAI or Anthropic is acceptable and the provider
must stay swappable so they can be A/B tested on the same corpus — comparative
quality data is itself a deliverable for an R&D project. Mistral is wired up
first because that is the key we have.

The interface is deliberately one method wide. Everything the gate needs is a
JSON object back from a prompt; anything richer belongs in the drafting agent
(Phase 3), not here.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol


@dataclass
class Completion:
    """A structured response plus the metadata the verdict log needs."""

    data: dict[str, Any]
    model: str
    usage: dict[str, Any] = field(default_factory=dict)
    latency_ms: int = 0
    raw: str = ""


class ProviderError(RuntimeError):
    pass


class Provider(Protocol):
    name: str

    def complete_json(self, system: str, user: str, *, model: str) -> Completion:
        """Return a parsed JSON object. Raise ProviderError on failure."""
        ...


def get(name: str) -> Provider:
    if name == "mistral":
        from .mistral import MistralProvider

        return MistralProvider()
    if name == "fake":
        from .fake import FakeProvider

        return FakeProvider()
    raise ProviderError(f"unknown provider {name!r} (known: mistral, fake)")
