"""Opening the docs merge request. Offline throughout: the forge is faked, the
same way the model is faked in test_gate.py."""

from __future__ import annotations

import json

import pytest
import yaml

from docbot import gate, propose, verdictlog
from docbot.forge import ForgeError
from docbot.forge.fake import FakeForge
from docbot.propose import ProposeError
from docbot.providers import Completion

DOCS = "root/mobivisor-manual"
SOURCE = "root/mobivisor-console"


class StubProvider:
    name = "stub"

    def __init__(self, **data):
        self.data = data

    def complete_json(self, system, user, *, model):
        return Completion(data=self.data, model="stub-1", usage={}, latency_ms=1)


def make_verdict(doc_map, tmp_path, files=("src/enrollment/ios/EnrollmentWizard.tsx",), **mr):
    """A real verdict from a real gate run — proposals must survive whatever
    shape the gate actually emits, not a hand-written approximation of it."""
    provider = StubProvider(
        user_facing=True, areas=["enrollment-ios"], confidence=0.87,
        reason="the enrollment wizard's step labels changed",
    )
    request = gate.MergeRequest(
        id=mr.get("id", "12"),
        title=mr.get("title", "Update iOS enrollment wizard copy"),
        author=mr.get("author", "root"),
        branch=mr.get("branch", "feature/enrollment-101010"),
        target=mr.get("target", "main"),
        url=mr.get("url", "http://gitlab.orb.local/root/mobivisor-console/-/merge_requests/12"),
    )
    return gate.run(doc_map, list(files), request, provider=provider, log_dir=str(tmp_path))


@pytest.fixture
def forge() -> FakeForge:
    return FakeForge()


def propose_run(verdict, forge, tmp_path, **kw):
    return propose.run(
        verdict, forge, docs_project=DOCS, source_project=SOURCE,
        log_dir=str(tmp_path), **kw,
    )


# -- the silent case -------------------------------------------------------


def silent_verdict(doc_map, tmp_path):
    provider = StubProvider(user_facing=False, areas=[], confidence=0.9, reason="internal")
    return gate.run(
        doc_map, ["src/protocol/apns/PushTransport.ts"], gate.MergeRequest(id="7"),
        provider=provider, log_dir=str(tmp_path),
    )


def test_silent_verdict_never_touches_the_forge(doc_map, tmp_path, forge):
    """§6.2 — no impact, exit silently. §14.3 — this is the common answer."""
    result = propose_run(silent_verdict(doc_map, tmp_path), forge, tmp_path)

    assert result["status"] == "skipped"
    assert forge.merge_requests == []
    assert forge.commits == []


def test_silent_verdict_needs_no_forge_at_all(doc_map, tmp_path):
    """Not the same assertion as above. Most merges are silent, so a silent run
    must complete without a forge URL or a token — otherwise every uneventful
    merge fails the build for want of a credential it never uses."""
    result = propose.run(
        silent_verdict(doc_map, tmp_path), None, docs_project=DOCS, log_dir=str(tmp_path)
    )
    assert result["status"] == "skipped"


# -- the merge gate --------------------------------------------------------
#
# The source merge request must have landed before anything is written. An open
# MR is a draft of an intention: it gets rewritten, rescoped and sometimes
# closed unmerged, and a docs reviewer cannot tell which of those they are
# looking at. This is §8.3's push-to-main trigger as a precondition.


def test_unmerged_source_is_deferred_not_proposed(doc_map, tmp_path):
    forge = FakeForge(merged=False)
    result = propose_run(make_verdict(doc_map, tmp_path), forge, tmp_path)

    assert result["status"] == "deferred"
    assert forge.merge_requests == []
    assert forge.commits == []
    assert forge.notes == []


def test_closed_source_is_abandoned_not_deferred(doc_map, tmp_path):
    """`opened` is "not yet"; `closed` is "never". A queue that cannot tell
    them apart fills with entries nobody will ever clear."""
    forge = FakeForge(merged=False)
    forge.merge.state = "closed"
    result = propose_run(make_verdict(doc_map, tmp_path), forge, tmp_path)

    assert result["status"] == "abandoned"
    assert "closed without merging" in result["reason"]
    assert forge.commits == []


def test_deferral_is_not_silence(doc_map, tmp_path):
    """`skipped` means the manual is unaffected; `deferred` means it is
    affected but the change has not shipped. Collapsing the two would hide a
    real doc impact behind the same word used for the 90% that are nothing."""
    deferred = propose_run(make_verdict(doc_map, tmp_path), FakeForge(merged=False), tmp_path)
    skipped = propose_run(silent_verdict(doc_map, tmp_path), FakeForge(), tmp_path)

    assert deferred["status"] == "deferred"
    assert deferred["doc_impact"] is True
    assert skipped["status"] == "skipped"
    assert skipped["doc_impact"] is False


def test_merge_state_that_cannot_be_read_defers_rather_than_assuming_yes(doc_map, tmp_path):
    """Fails closed, opposite to the gate. The gate's failure mode is a change
    nobody looked at; this module's is documenting work that never shipped."""

    class Unreachable(FakeForge):
        def merge_state(self, project, merge_request):
            raise ForgeError("500 internal error")

    forge = Unreachable()
    result = propose_run(make_verdict(doc_map, tmp_path), forge, tmp_path)

    assert result["status"] == "deferred"
    assert "500" in result["reason"]
    assert forge.commits == []


def test_merge_is_recorded_as_provenance(doc_map, tmp_path):
    forge = FakeForge(merged=True, merged_by="alice")
    result = propose_run(make_verdict(doc_map, tmp_path), forge, tmp_path, doc_map=doc_map)

    assert result["status"] == "created"
    assert result["merge"]["merged_by"] == "alice"

    record = yaml.safe_load(forge.files[(DOCS, result["branch"])][result["record_path"]])
    merge = record["source"]["merge"]
    assert (merge["merged"], merge["merged_by"], merge["merge_commit"]) == (True, "alice", "deadbeef")
    body = forge.merge_requests[0]["description"]
    assert "merged" in body.lower() and "alice" in body


def test_override_says_so_in_the_body(doc_map, tmp_path):
    """--allow-unmerged is legitimate, but the docs reviewer has to be told
    they are looking at a change that has not shipped."""
    forge = FakeForge(merged=False)
    result = propose_run(make_verdict(doc_map, tmp_path), forge, tmp_path, require_merged=False)

    assert result["status"] == "created"
    assert result["merge"] is None
    assert "not checked" in forge.merge_requests[0]["description"]


def test_merge_check_needs_to_know_which_project_to_ask(doc_map, tmp_path, forge):
    with pytest.raises(ProposeError, match="source-project"):
        propose.run(
            make_verdict(doc_map, tmp_path), forge, docs_project=DOCS,
            source_project="", log_dir=str(tmp_path),
        )


def test_silent_verdict_is_not_delayed_by_the_merge_check(doc_map, tmp_path):
    """No doc impact means nothing to propose whether or not it merged, so the
    check must not run — it would be a pointless API call on the vast majority
    of merges."""

    class NoMergeState(FakeForge):
        def merge_state(self, project, merge_request):
            raise AssertionError("merge state must not be checked for a silent verdict")

    result = propose_run(silent_verdict(doc_map, tmp_path), NoMergeState(), tmp_path)
    assert result["status"] == "skipped"


# -- the merge request -----------------------------------------------------


def test_opens_one_merge_request_carrying_the_record(doc_map, tmp_path, forge):
    result = propose_run(make_verdict(doc_map, tmp_path), forge, tmp_path)

    assert result["status"] == "created"
    assert len(forge.merge_requests) == 1
    mr = forge.merge_requests[0]
    assert mr["project"] == DOCS
    assert mr["target_branch"] == "main"
    assert mr["source_branch"].startswith("docbot/mr-12")
    # Exactly one file, in the ledger directory. The docs MR must not sprawl.
    assert list(forge.files[(DOCS, mr["source_branch"])]) == ["doc-impact/pending/mr-12.yaml"]
    assert result["record_path"] == "doc-impact/pending/mr-12.yaml"


def test_record_is_valid_yaml_and_names_the_pages(doc_map, tmp_path, forge):
    result = propose_run(make_verdict(doc_map, tmp_path), forge, tmp_path, doc_map=doc_map)

    written = forge.files[(DOCS, result["branch"])][result["record_path"]]
    record = yaml.safe_load(written)

    assert record["schema"] == propose.RECORD_SCHEMA
    assert record["source"]["merge_request"] == "12"
    assert record["source"]["project"] == SOURCE
    assert record["gate"]["confidence"] == 0.87
    assert record["gate"]["areas"] == ["enrollment-ios"]
    assert [p["path"] for p in record["pages"]] == ["pages/enrollment/ios-abm.md"]
    assert record["pages"][0]["class"] == "ai-drafted"


def test_record_carries_no_diff(doc_map, tmp_path, forge):
    """§10 governance again, one repository further along: the gate keeps diffs
    off the network, and the record must not put them back in a docs repo that
    a wider audience can read."""
    result = propose_run(make_verdict(doc_map, tmp_path), forge, tmp_path)
    written = forge.files[(DOCS, result["branch"])][result["record_path"]]
    for marker in ("@@", "+++", "diff --git"):
        assert marker not in written


def test_description_tells_the_reviewer_what_it_is_not(doc_map, tmp_path, forge):
    propose_run(make_verdict(doc_map, tmp_path), forge, tmp_path, doc_map=doc_map)
    body = forge.merge_requests[0]["description"]

    assert "!12" in body                              # linked back to the source MR (§7 B)
    assert "pages/enrollment/ios-abm.md" in body
    assert "No prose has been drafted" in body
    assert "No change needed" in body or "no change needed" in body.lower()


def test_body_does_not_credit_the_model_with_a_deterministic_override(doc_map, tmp_path, forge):
    """A touched `generated` area makes doc_impact true whatever tier 2 said
    (§14.2). Reporting that as the model's verdict would mislead exactly the
    reviewer whose job is to judge the model."""
    provider = StubProvider(user_facing=False, areas=[], confidence=0.95, reason="schema only")
    verdict = gate.run(
        doc_map, ["schema/policies/android.json"],
        gate.MergeRequest(id="21", title="Add Android restriction key"),
        provider=provider, log_dir=str(tmp_path),
    )
    result = propose_run(verdict, forge, tmp_path, doc_map=doc_map)

    assert result["status"] == "created"
    body = forge.merge_requests[0]["description"]
    assert "user_facing=`false`" in body
    assert "deterministic rule overrode it" in body

    record = yaml.safe_load(forge.files[(DOCS, result["branch"])][result["record_path"]])
    assert record["gate"]["model_user_facing"] is False
    assert record["gate"]["doc_impact"] is True


def test_never_targets_the_docs_default_branch(doc_map, tmp_path, forge):
    verdict = make_verdict(doc_map, tmp_path)
    with pytest.raises(ProposeError):
        propose_run(verdict, forge, tmp_path, target_branch=propose.branch_name(verdict))


def test_missing_mr_id_is_refused(doc_map, tmp_path, forge):
    """An unstable branch name means a new docs MR on every push."""
    verdict = make_verdict(doc_map, tmp_path, id="")
    with pytest.raises(ProposeError):
        propose_run(verdict, forge, tmp_path)


# -- idempotency -----------------------------------------------------------


def test_second_run_updates_rather_than_opening_a_second_merge_request(doc_map, tmp_path, forge):
    """A source MR is pushed to repeatedly; each push re-runs the gate."""
    first = propose_run(make_verdict(doc_map, tmp_path), forge, tmp_path)

    later = make_verdict(doc_map, tmp_path, files=[
        "src/enrollment/ios/EnrollmentWizard.tsx", "src/enrollment/ios/DepProfile.tsx",
    ])
    second = propose_run(later, forge, tmp_path)

    assert first["status"] == "created"
    assert second["status"] == "updated"
    assert len(forge.merge_requests) == 1
    assert second["branch"] == first["branch"]

    record = yaml.safe_load(forge.files[(DOCS, second["branch"])][second["record_path"]])
    assert "src/enrollment/ios/DepProfile.tsx" in record["source"]["changed_files"]
    # The body was rewritten too, or it would describe the first verdict forever.
    assert "DepProfile.tsx" in forge.merge_requests[0]["description"]


# -- the comment back on the source MR -------------------------------------


def test_comment_source_links_the_two_merge_requests(doc_map, tmp_path, forge):
    result = propose_run(make_verdict(doc_map, tmp_path), forge, tmp_path, comment_source=True)

    assert len(forge.notes) == 1
    note = forge.notes[0]
    assert note["project"] == SOURCE
    assert note["merge_request"] == "12"
    assert result["merge_request"]["url"] in note["body"]


def test_comment_failure_does_not_lose_the_merge_request(doc_map, tmp_path):
    class NoComments(FakeForge):
        def comment(self, project, merge_request, body):
            raise ForgeError("403 bot has no access to the source project")

    forge = NoComments()
    result = propose_run(make_verdict(doc_map, tmp_path), forge, tmp_path, comment_source=True)

    assert result["status"] == "created"
    assert "403" in result["warning"]
    assert len(forge.merge_requests) == 1


# -- the log ---------------------------------------------------------------


def test_every_proposal_is_logged_separately_from_verdicts(doc_map, tmp_path, forge):
    """§14.4 — log every verdict and every draft."""
    propose_run(make_verdict(doc_map, tmp_path), forge, tmp_path)
    propose_run(make_verdict(doc_map, tmp_path, id="13"), forge, tmp_path)

    proposals = verdictlog.read(tmp_path, verdictlog.PROPOSAL_LOG_NAME)
    assert len(proposals) == 2
    assert {p["schema"] for p in proposals} == {propose.SCHEMA}
    # The gate's dataset stays uncontaminated by delivery records.
    assert all(v["schema"] == gate.SCHEMA for v in verdictlog.read(tmp_path))


def test_result_is_json_serialisable(doc_map, tmp_path, forge):
    json.dumps(propose_run(make_verdict(doc_map, tmp_path), forge, tmp_path))
