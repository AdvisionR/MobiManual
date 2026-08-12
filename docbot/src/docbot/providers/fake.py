"""Deterministic stand-in provider.

Exists so the whole gate — including tier 2 — can be exercised in tests and in
offline eval runs without a network call or a bill. It is a crude keyword
heuristic and makes no claim to be good; its value is that it is *stable*, so a
failing test means the pipeline broke rather than the model drifted.
"""

from __future__ import annotations

import json

from . import Completion

#: Paths that read as user-facing surface area.
USER_FACING_HINTS = ("/ui/", "/console/", "/enrollment/", "/pages/", ".tsx", "wizard", "schema/")

#: Paths that read as internals regardless of anything else.
INTERNAL_HINTS = ("/protocol/", "/transport/", "/internal/", "test", "spec")


class FakeProvider:
    name = "fake"

    def complete_json(self, system: str, user: str, *, model: str) -> Completion:
        haystack = user.lower()
        hits = sum(1 for hint in USER_FACING_HINTS if hint in haystack)
        internal = sum(1 for hint in INTERNAL_HINTS if hint in haystack)
        user_facing = hits > internal

        # Echo back any candidate area ids the prompt offered, so the tier-2
        # area-validation path is genuinely exercised rather than short-circuited.
        areas = [
            line.split("`")[1]
            for line in user.splitlines()
            if line.strip().startswith("- `") and "`" in line[4:]
        ]

        data = {
            "user_facing": user_facing,
            "areas": areas if user_facing else [],
            "confidence": 0.9 if abs(hits - internal) > 1 else 0.5,
            "reason": f"fake provider: {hits} user-facing hint(s), {internal} internal hint(s)",
        }
        return Completion(
            data=data,
            model="fake-1",
            usage={"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0},
            latency_ms=0,
            raw=json.dumps(data),
        )
