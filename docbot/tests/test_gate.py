"""Gate orchestration. The model is faked throughout — these tests are about
the decision logic around it, which is where the costly mistakes live."""

from __future__ import annotations

import json

from docbot import gate, verdictlog
from docbot.providers import Completion, ProviderError
from docbot.providers.fake import FakeProvider


class StubProvider:
    """Returns whatever verdict the test asks for."""

    name = "stub"

    def __init__(self, **data):
        self.data = data
        self.prompts: list[str] = []

    def complete_json(self, system, user, *, model):
        self.prompts.append(user)
        return Completion(data=self.data, model="stub-1", usage={}, latency_ms=1)


class BrokenProvider:
    name = "broken"

    def complete_json(self, system, user, *, model):
        raise ProviderError("429 rate limited")


def run(doc_map, files, tmp_path, provider=None, **kw):
    return gate.run(
        doc_map,
        files,
        gate.MergeRequest(id="1", title=kw.pop("title", "test")),
        provider=provider or FakeProvider(),
        log_dir=str(tmp_path),
        **kw,
    )


def test_silent_merge_never_calls_the_model(doc_map, tmp_path):
    provider = StubProvider(user_facing=True, areas=[], confidence=1.0, reason="should not run")
    verdict = run(doc_map, ["src/protocol/apns/PushTransport.ts"], tmp_path, provider)
    assert verdict["doc_impact"] is False
    assert verdict["tier_reached"] == 1
    assert provider.prompts == []


def test_generated_area_decides_without_the_model(doc_map, tmp_path):
    """§14.2 — deterministic beats probabilistic. A schema change means the
    reference tables are stale; that is a fact, not a judgement."""
    provider = StubProvider(user_facing=False, areas=[], confidence=0.99, reason="model says no")
    verdict = run(doc_map, ["schema/policies/android.json"], tmp_path, provider)
    assert verdict["doc_impact"] is True
    assert "render-reference" in verdict["actions"]


def test_model_negative_keeps_the_gate_quiet(doc_map, tmp_path):
    provider = StubProvider(user_facing=False, areas=[], confidence=0.9, reason="internal refactor")
    verdict = run(doc_map, ["src/enrollment/ios/EnrollmentWizard.tsx"], tmp_path, provider)
    assert verdict["doc_impact"] is False
    assert verdict["tier_reached"] == 2


def test_model_positive_yields_pages_and_a_draft_action(doc_map, tmp_path):
    provider = StubProvider(
        user_facing=True, areas=["enrollment-ios"], confidence=0.9, reason="wizard copy changed"
    )
    verdict = run(doc_map, ["src/enrollment/ios/EnrollmentWizard.tsx"], tmp_path, provider)
    assert verdict["doc_impact"] is True
    assert verdict["areas"] == ["enrollment-ios"]
    assert verdict["pages"] == ["pages/enrollment/ios-abm.md"]
    assert "draft" in verdict["actions"]


def test_invented_area_ids_are_rejected_not_trusted(doc_map, tmp_path):
    provider = StubProvider(
        user_facing=True,
        areas=["enrollment-ios", "chapter-42-teleportation"],
        confidence=0.8,
        reason="",
    )
    verdict = run(doc_map, ["src/enrollment/ios/EnrollmentWizard.tsx"], tmp_path, provider)
    assert verdict["areas"] == ["enrollment-ios"]
    assert verdict["tier2"]["rejected_areas"] == ["chapter-42-teleportation"]


def test_human_only_area_never_gets_a_draft_action(doc_map, tmp_path):
    """§6.4 — the agent must never edit these pages."""
    provider = StubProvider(
        user_facing=True, areas=["security-statements"], confidence=0.9, reason="wording"
    )
    verdict = run(doc_map, ["docs/security/data-residency.md"], tmp_path, provider)
    assert verdict["doc_impact"] is True
    assert "human-review" in verdict["actions"]
    assert "draft" not in verdict["actions"]


def test_provider_failure_degrades_to_human_triage(doc_map, tmp_path):
    """A gate that crashes blocks merges."""
    verdict = run(doc_map, ["src/enrollment/ios/EnrollmentWizard.tsx"], tmp_path, BrokenProvider())
    assert verdict["doc_impact"] is True
    assert verdict["tier2"]["ran"] is False
    assert "429" in verdict["tier2"]["error"]
    assert any("tier 2 unavailable" in n for n in verdict["notes"])


def test_low_confidence_is_flagged_for_a_human(doc_map, tmp_path):
    provider = StubProvider(user_facing=True, areas=["enrollment-ios"], confidence=0.2, reason="unsure")
    verdict = run(doc_map, ["src/enrollment/ios/EnrollmentWizard.tsx"], tmp_path, provider)
    assert "human-review" in verdict["actions"]


def test_no_model_flag_makes_no_call(doc_map, tmp_path):
    provider = StubProvider(user_facing=True, areas=[], confidence=1.0, reason="")
    verdict = run(doc_map, ["src/enrollment/ios/EnrollmentWizard.tsx"], tmp_path, provider, use_model=False)
    assert provider.prompts == []
    assert verdict["tier_reached"] == 1
    # Conservative: tier 1 flagged it and tier 2 was unavailable to clear it.
    assert verdict["doc_impact"] is True


def test_prompt_carries_no_diff_only_paths(doc_map, tmp_path):
    """§10 governance: diffs must not leave the network."""
    provider = StubProvider(user_facing=False, areas=[], confidence=0.9, reason="")
    run(doc_map, ["src/enrollment/ios/EnrollmentWizard.tsx"], tmp_path, provider)
    prompt = provider.prompts[0]
    assert "EnrollmentWizard.tsx" in prompt
    assert "enrollment-ios" in prompt
    for diff_marker in ("@@", "+++", "---", "diff --git"):
        assert diff_marker not in prompt


def test_every_verdict_is_logged(doc_map, tmp_path):
    """§14.4 — log every verdict; the data is the output."""
    run(doc_map, ["src/protocol/apns/PushTransport.ts"], tmp_path)
    run(doc_map, ["src/enrollment/ios/EnrollmentWizard.tsx"], tmp_path)
    logged = verdictlog.read(tmp_path)
    assert len(logged) == 2
    assert {entry["schema"] for entry in logged} == {gate.SCHEMA}


def test_verdict_is_json_serialisable(doc_map, tmp_path):
    verdict = run(doc_map, ["src/console/roles/RolesTable.tsx"], tmp_path)
    json.dumps(verdict)
