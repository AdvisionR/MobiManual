from docbot.draft import HEADER, draft

MR = {"iid": 4, "title": "Rework the iOS wizard", "author": {"username": "dev"}, "web_url": "http://gl/mr/4"}


def test_new_file_gets_header_and_section():
    diffs = [{"old_path": "a.js", "new_path": "a.js", "diff": "@@ -1 +1 @@\n-x\n+y\n"}]
    text = draft(None, MR, diffs)
    assert text.startswith(HEADER)
    assert "## !4: Rework the iOS wizard" in text
    assert "````diff\n@@ -1 +1 @@\n-x\n+y\n````" in text
    assert text.endswith("\n")


def test_existing_file_is_kept_and_extended():
    current = "# Changes seen by DocBot\n\n## !3: earlier\n"
    renamed = [{"old_path": "old.js", "new_path": "new.js", "diff": ""}]
    text = draft(current, MR, renamed)
    assert text.startswith(current)
    assert "### old.js -> new.js" in text
    assert "(no textual diff)" in text
