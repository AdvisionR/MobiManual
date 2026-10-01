"""The manual as the model sees it: the table of contents, read_page and search_manual."""

import pytest

from docbot.drafting.manual import (
    MAX_MATCHES,
    MAX_PAGE_LINES,
    Manual,
    ManualError,
    headings,
    html_doc_pages,
)
from docbot.llm.agent import ToolError

GRUNTFILE = """\
// search.md and break.md are not listed.
var htmlDocPages = [
  'cover_page.md',
  '_devices.md',
  '_devices_id.md'
];
var languages = ['en', 'tr', 'de'];
"""


def test_the_page_list_is_read_like_check_missing_doc_reads_it():
    assert html_doc_pages(GRUNTFILE) == ["cover_page.md", "_devices.md", "_devices_id.md"]


def test_a_gruntfile_without_the_page_list_is_an_error():
    with pytest.raises(ManualError, match="htmlDocPages not found"):
        html_doc_pages("module.exports = function () {};")


def test_headings_skip_fenced_code_and_closing_hashes():
    text = "# Devices\n\nText #not a heading\n\n```bash\n# a comment\n```\n\n## Filters ##\n#hashtag\n"
    assert headings(text) == ["# Devices", "## Filters"]


def test_contents_lists_pages_in_order_with_headings_and_marks_edited_ones():
    manual = Manual({"cover_page.md": "% MobiVisor User Manual\n",
                     "_devices.md": "# Devices\n\n## Filters\n",
                     "_devices_id.md": "# Device details\n"})
    assert manual.contents(edited=["_devices_id.md"]) == (
        "cover_page.md\n"
        "_devices.md\n    # Devices\n    ## Filters\n"
        "_devices_id.md (already edited in this merge request)\n    # Device details")


def test_a_front_matter_title_is_the_first_heading():
    page = '---\ntitle: "Edit a message"\nsidebar: x\n---\n\nimport X from "y";\n\n## Edit a message\n'
    assert headings(page) == ["# Edit a message", "## Edit a message"]
    assert headings("---\nsidebar: x\n---\ntitle: not front matter\n") == []


MANUAL = Manual({"_users.md": "# Users\n\n1. Open **Users**.\n2. Select **Save**.\n",
                 "_devices.md": "# Devices\n\nThe enrolled filter hides retired devices.\n"})


def test_read_page_returns_the_text_as_an_edit_must_quote_it():
    assert MANUAL.read_page("_users.md") == "_users.md, lines 1-4 of 4:\n# Users\n\n1. Open **Users**.\n2. Select **Save**."


def test_a_long_page_is_read_in_parts():
    manual = Manual({"long.md": "\n".join(f"line {n}" for n in range(1, MAX_PAGE_LINES + 11))})
    first = manual.read_page("long.md")
    assert first.startswith(f"long.md, lines 1-{MAX_PAGE_LINES} of {MAX_PAGE_LINES + 10}; read on with start=")
    assert manual.read_page("long.md", start=MAX_PAGE_LINES + 1).endswith(f"line {MAX_PAGE_LINES + 10}")


def test_search_finds_every_page_that_mentions_a_term():
    assert MANUAL.search("save|enrolled") == "_users.md:4: 2. Select **Save**.\n_devices.md:3: The enrolled filter hides retired devices."
    assert MANUAL.search("kiosk") == "no page matches 'kiosk'"


def test_search_results_are_capped():
    manual = Manual({"a.md": "x\n" * (MAX_MATCHES + 5)})
    assert manual.search("x").endswith("... 5 more matching lines; narrow the pattern")


@pytest.mark.parametrize("call, message", [
    (lambda h: h["read_page"]({"page": "_kiosk.md"}), "no page '_kiosk.md'"),
    (lambda h: h["read_page"]({"page": "_users.md", "start": 9}), "has only 4 lines"),
    (lambda h: h["read_page"]({}), "'page' must be a string"),
    (lambda h: h["search_manual"]({"pattern": "("}), "not a valid regular expression"),
])
def test_tool_errors_go_back_to_the_model(call, message):
    _, handlers = MANUAL.tools()
    with pytest.raises(ToolError, match=message):
        call(handlers)


ZULIP = Manual({"docs/link-to-a-message.mdx": "a\n", "docs/left-sidebar.mdx": "b\n", "include/_Steps.mdx": "c\n",
                "docs/steps.mdx": "d\n", "other/steps.mdx": "e\n"})


@pytest.mark.parametrize("name", ["docs/link-to-a-message.mdx", "link-to-a-message", "link-to-a-message.mdx",
                                  "docs/link-to-a-message"])
def test_a_page_can_be_named_without_its_folder_or_extension(name):
    assert ZULIP.read_page(name).startswith("docs/link-to-a-message.mdx, lines 1-1 of 1:")


def test_a_short_name_that_fits_several_pages_is_refused():
    with pytest.raises(ToolError, match="fits several pages: docs/steps.mdx, other/steps.mdx"):
        ZULIP.read_page("steps")


def test_an_unknown_page_comes_with_the_closest_names():
    with pytest.raises(ToolError, match="did you mean docs/left-sidebar.mdx"):
        ZULIP.read_page("left-sidebr")
