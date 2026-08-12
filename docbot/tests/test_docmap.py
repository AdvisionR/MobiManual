"""Tier 1 is the tier that must never be wrong: it runs on every merge and it
decides, for free, whether anything else happens at all."""

from __future__ import annotations

import pytest

from docbot import docmap
from docbot.docmap import DocMapError


def write(tmp_path, text: str):
    path = tmp_path / "doc-map.yaml"
    path.write_text(text, encoding="utf-8")
    return path


def test_loads_the_shipped_example(doc_map):
    assert "enrollment-ios" in doc_map.ids
    assert doc_map.area("policy-schema").klass == "generated"
    assert doc_map.escalate_unmapped is True


def test_rejects_unknown_class(tmp_path):
    path = write(tmp_path, """
areas:
  - id: a
    code: ["^src/"]
    pages: ["p.adoc"]
    class: probably-fine
""")
    with pytest.raises(DocMapError, match="class must be one of"):
        docmap.load(path)


def test_rejects_doc_relevant_area_with_no_pages(tmp_path):
    """The most common editing slip: an area that can never point anywhere."""
    path = write(tmp_path, """
areas:
  - id: a
    code: ["^src/"]
    pages: []
    class: ai-drafted
""")
    with pytest.raises(DocMapError, match="no pages listed"):
        docmap.load(path)


def test_rejects_duplicate_ids(tmp_path):
    path = write(tmp_path, """
areas:
  - id: a
    code: ["^src/"]
    pages: ["p.adoc"]
    class: ai-drafted
  - id: a
    code: ["^lib/"]
    pages: ["q.adoc"]
    class: ai-drafted
""")
    with pytest.raises(DocMapError, match="duplicate id"):
        docmap.load(path)


def test_rejects_bad_regex(tmp_path):
    path = write(tmp_path, """
areas:
  - id: a
    code: ["^src/(unclosed"]
    pages: ["p.adoc"]
    class: ai-drafted
""")
    with pytest.raises(DocMapError, match="bad regex"):
        docmap.load(path)


# ---- tier 1 behaviour -----------------------------------------------------


def test_doc_relevant_area_escalates(doc_map):
    result = docmap.tier1(doc_map, ["src/enrollment/ios/EnrollmentWizard.tsx"])
    assert result.escalate is True
    assert [h.area.id for h in result.hits] == ["enrollment-ios"]


def test_only_no_doc_impact_areas_stay_silent(doc_map):
    """§14.3 — the gate's job is mostly to say nothing."""
    result = docmap.tier1(doc_map, ["src/protocol/apns/PushTransport.ts"])
    assert result.escalate is False
    assert "no-doc-impact" in result.reason


def test_unmapped_files_escalate_as_a_possible_gap(doc_map):
    result = docmap.tier1(doc_map, ["src/shared/dates.ts"])
    assert result.escalate is True
    assert result.unmapped == ["src/shared/dates.ts"]
    assert "doc-map gap" in result.reason


def test_ignored_files_do_not_escalate(doc_map):
    result = docmap.tier1(doc_map, ["package-lock.json"])
    assert result.escalate is False
    assert result.ignored == ["package-lock.json"]
    assert result.unmapped == []


def test_a_single_relevant_file_outweighs_noise(doc_map):
    result = docmap.tier1(
        doc_map,
        ["Jenkinsfile", "package-lock.json", "src/console/roles/RolesTable.tsx"],
    )
    assert result.escalate is True
    assert [h.area.id for h in result.doc_relevant_hits] == ["users-and-roles"]


def test_a_file_can_match_several_areas(doc_map):
    """Overlapping patterns are legitimate; every hit must be reported so the
    verdict names all affected pages."""
    result = docmap.tier1(doc_map, ["src/policies/kiosk/validate.ts", "schema/policies/android.json"])
    assert {h.area.id for h in result.hits} == {"kiosk-modes", "policy-schema"}
