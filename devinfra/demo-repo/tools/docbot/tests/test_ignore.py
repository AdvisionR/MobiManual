"""The doc map's ignore list, against the kinds of test merge request open-test-mr.sh makes."""

import pytest

from docbot.drafting.ignore import select

# The fixture's ignore list, copied: these tests must pass where the fixture is not next to them.
DOC_MAP = {"docRoot": "public/doc", "ignore": [
    {"id": "ci-and-tests", "code": ["^\\.gitlab-ci\\.yml$", "^Jenkinsfile$", "^e2e/", "\\.spec\\.js$"]},
    {"id": "docbot", "code": ["^tools/docbot/"]},
    {"id": "manual-source", "code": ["^public/doc/"]},
]}
PAGE_DIR = "public/doc/en"


def diff(path: str, old_path: str | None = None, **flags) -> dict:
    return {"old_path": old_path or path, "new_path": path, "diff": "@@ -1 +1 @@\n+x\n", **flags}


# open-test-mr.sh's kinds: the files each one touches, and whether the model sees the merge request.
@pytest.mark.parametrize("kind, files, sent", [
    ("code", ["public/app/enrollment/ios/enrollment-wizard.controller.js"], True),
    ("kiosk", ["public/app/policies/kiosk/kiosk.controller.js"], True),
    ("users", ["public/app/users/users.controller.js"], True),
    ("devices", ["public/app/devices/devices.controller.js"], True),
    ("schema", ["schema/policies/android-restrictions.json"], True),
    ("internal", ["server/protocol/apns/push-transport.js"], True),
    ("ci", ["e2e/specs/devices.spec.js"], False),
    ("docs", ["public/doc/en/_users.md"], False),
    ("both", ["public/app/enrollment/ios/enrollment-wizard.controller.js", "public/doc/en/_enrollment_ios.md"], True),
    ("unmapped", ["public/app/reports/export-schedule.controller.js"], True),
])
def test_open_test_mr_kinds(kind, files, sent):
    selection = select(DOC_MAP, [diff(f) for f in files], PAGE_DIR)
    assert bool(selection.relevant) is sent


def test_ignored_files_are_dropped_and_logged():
    selection = select(DOC_MAP, [diff("public/app/a.js"), diff("tools/docbot/src/x.py"), diff("Jenkinsfile")], PAGE_DIR)
    assert [d["new_path"] for d in selection.relevant] == ["public/app/a.js"]
    assert selection.ignored == ["tools/docbot/src/x.py", "Jenkinsfile"]


def test_pages_the_merge_request_edited_are_remembered_but_not_sent():
    selection = select(DOC_MAP, [diff("public/app/a.js"), diff("public/doc/en/_enrollment_ios.md"),
                                 diff("public/doc/de/_enrollment_ios.md")], PAGE_DIR)
    assert selection.edited_pages == ["_enrollment_ios.md"]
    assert [d["new_path"] for d in selection.relevant] == ["public/app/a.js"]


def test_a_deleted_page_is_not_an_edited_one():
    selection = select(DOC_MAP, [diff("public/doc/en/_old.md", deleted_file=True)], PAGE_DIR)
    assert selection.edited_pages == []


def test_a_file_moved_out_of_an_ignored_area_is_sent():
    selection = select(DOC_MAP, [diff("public/app/helper.js", old_path="e2e/helper.js")], PAGE_DIR)
    assert len(selection.relevant) == 1
