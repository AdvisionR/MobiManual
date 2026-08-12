"""The eval harness is how the gate gets tuned without touching Jenkins (§8.6)."""

from __future__ import annotations

from docbot import evalharness
from docbot.providers.fake import FakeProvider


def test_corpus_parses_and_is_balanced(corpus_path):
    """A corpus of all-positives would make a gate that always says yes look
    perfect. §14.3 makes silence the common correct answer, so the corpus has
    to test for it."""
    cases = evalharness.load_corpus(corpus_path)
    assert len(cases) == 10
    positives = sum(1 for c in cases if c["expected_doc_impact"])
    assert positives == 5


def test_tier1_only_baseline_scores_without_a_model(doc_map, corpus_path, tmp_path):
    report = evalharness.run(
        doc_map, evalharness.load_corpus(corpus_path), use_model=False, log_dir=str(tmp_path)
    )
    confusion = report["confusion"]
    assert confusion["TP"] + confusion["FP"] + confusion["TN"] + confusion["FN"] == 10
    # Tier 1 alone escalates anything it cannot rule out, so it should catch
    # every true positive and pay for it in false positives.
    assert confusion["FN"] == 0
    assert confusion["FP"] > 0


def test_fake_provider_run_is_deterministic(doc_map, corpus_path, tmp_path):
    cases = evalharness.load_corpus(corpus_path)
    first = evalharness.run(doc_map, cases, provider=FakeProvider(), log_dir=str(tmp_path))
    second = evalharness.run(doc_map, cases, provider=FakeProvider(), log_dir=str(tmp_path))
    assert first["confusion"] == second["confusion"]
    assert first["accuracy"] == second["accuracy"]


def test_confusion_matrix_arithmetic(doc_map, tmp_path):
    cases = [
        {"id": "yes", "changed_files": ["schema/policies/x.json"], "expected_doc_impact": True},
        {"id": "no", "changed_files": ["src/protocol/apns/x.ts"], "expected_doc_impact": False},
    ]
    report = evalharness.run(doc_map, cases, use_model=False, log_dir=str(tmp_path))
    assert report["confusion"] == {"TP": 1, "FP": 0, "TN": 1, "FN": 0}
    assert report["accuracy"] == 1.0
    assert report["precision"] == 1.0
    assert report["recall"] == 1.0
    assert report["false_positive_rate"] == 0.0
