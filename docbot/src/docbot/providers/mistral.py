"""Mistral provider.

Plain HTTP against the chat-completions endpoint rather than the vendor SDK:
one fewer dependency in the CI image, and the request shape is close enough to
OpenAI's that a second provider is a copy of this file with a different base
URL.
"""

from __future__ import annotations

import json
import time
from typing import Any

import httpx

from ..config import api_key
from . import Completion, ProviderError

API_URL = "https://api.mistral.ai/v1/chat/completions"
TIMEOUT = 60.0


class MistralProvider:
    name = "mistral"

    def __init__(self, key: str | None = None, url: str = API_URL) -> None:
        self._key = key or api_key("mistral")
        self._url = url

    def complete_json(self, system: str, user: str, *, model: str) -> Completion:
        if not self._key:
            raise ProviderError(
                "MISTRAL_API_KEY is not set. Export it, or put it in the "
                "repository-root .env. In CI it comes from withCredentials."
            )

        payload: dict[str, Any] = {
            "model": model,
            # Zero temperature: the gate is a classifier, not a writer, and a
            # reproducible verdict is worth more than a varied one. §14.4 —
            # the logged verdicts are the research output.
            "temperature": 0,
            "response_format": {"type": "json_object"},
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
        }

        started = time.monotonic()
        try:
            response = httpx.post(
                self._url,
                headers={"Authorization": f"Bearer {self._key}"},
                json=payload,
                timeout=TIMEOUT,
            )
        except httpx.HTTPError as exc:
            raise ProviderError(f"mistral request failed: {exc}") from exc
        latency_ms = int((time.monotonic() - started) * 1000)

        if response.status_code != 200:
            raise ProviderError(
                f"mistral returned HTTP {response.status_code}: {response.text[:400]}"
            )

        body = response.json()
        try:
            content = body["choices"][0]["message"]["content"]
        except (KeyError, IndexError) as exc:
            raise ProviderError(f"unexpected response shape: {json.dumps(body)[:400]}") from exc

        try:
            data = json.loads(content)
        except json.JSONDecodeError as exc:
            # Should not happen with response_format=json_object, but a gate
            # that crashes on a malformed verdict is a gate that blocks merges.
            raise ProviderError(f"model did not return JSON: {content[:400]}") from exc

        return Completion(
            data=data,
            model=body.get("model", model),
            usage=body.get("usage", {}),
            latency_ms=latency_ms,
            raw=content,
        )
