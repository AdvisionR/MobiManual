import pytest

from docbot.drafting.edits import EditError, apply, wrap_width

PAGE = "1. Open **Policies > Kiosk**.\n2. Select **Save**.\n\nLeaving kiosk mode requires the device passcode.\n"


def test_edits_apply_in_order():
    new = apply(PAGE, [
        {"find": "requires the device passcode.", "replace": "requires the policy's exit passcode."},
        {"find": "the policy's exit passcode.", "replace": "the exit passcode set in the policy."},
    ])
    assert new.endswith("Leaving kiosk mode requires the exit passcode set in the policy.\n")


def test_a_snippet_copied_onto_one_line_still_matches_a_wrapped_page():
    wrapped = "Use the platform filter. The enrolled\nfilter hides devices that have been wiped.\n"
    new = apply(wrapped, [{"find": "The enrolled filter hides devices", "replace": "The compliance filter"}])
    assert new == "Use the platform filter. The\ncompliance filter that have been\nwiped.\n"


DEVICES = """\
# Devices

![](screenshots/_devices_1.png)

Use the platform filter to restrict the list to Android or iOS. The enrolled
filter hides devices that have been wiped or retired.
"""
ONE_LINE = "Use the platform filter to restrict the list to Android or iOS. The enrolled filter hides devices that have been wiped or retired."


def test_a_paragraph_the_model_joined_onto_one_line_is_wrapped_again():
    # The devices-filter scenario, as Mistral drafted it on 2026-10-01.
    replace = ONE_LINE.replace(" The enrolled", " Use the compliance filter to show all, compliant, or "
                                                "non-compliant devices. The enrolled")
    assert apply(DEVICES, [{"find": ONE_LINE, "replace": replace}]).endswith(
        "\n\nUse the platform filter to restrict the list to Android or iOS. Use the\n"
        "compliance filter to show all, compliant, or non-compliant devices. The\n"
        "enrolled filter hides devices that have been wiped or retired.\n")


def test_the_models_own_line_breaks_are_kept_and_a_trailing_space_dropped():
    replace = ("Use the platform filter to restrict the list to Android or iOS. \nUse the compliance filter to show "
               "all, compliant or non-compliant devices. The enrolled filter hides devices that have been wiped or retired.")
    assert apply(DEVICES, [{"find": ONE_LINE, "replace": replace}]).endswith(
        "\n\nUse the platform filter to restrict the list to Android or iOS.\n"
        "Use the compliance filter to show all, compliant or non-compliant devices.\n"
        "The enrolled filter hides devices that have been wiped or retired.\n")


def test_a_long_list_item_continues_under_its_text():
    page = "Select the options the device should\nget, then continue.\n\n1. Open it.\n2. Save.\n"
    new = apply(page, [{"find": "2. Save.", "replace": "2. Select the department the device belongs to, then save it."}])
    assert new.endswith("1. Open it.\n2. Select the department the device\n   belongs to, then save it.\n")


def test_words_a_break_spills_over_join_the_next_line_of_the_paragraph():
    # The passcode-history scenario, as Mistral drafted it on 2026-10-08: wrapped a little wider than the page,
    # which left "When" and "and" on lines of their own before the spill-over joined the next line.
    page = ("After the set number of failed attempts, the device wipes itself. This cannot\nbe undone.\n\n"
            "If a user has forgotten the passcode, send **Clear passcode** from the device's\n**Commands** tab.\n")
    replace = ("be undone.\n\nThe passcode history setting prevents users from reusing their last passcodes. When\n"
               "the value is greater than 0, the device remembers that many previous passcodes and\n"
               "rejects any attempt to reuse one of them.")
    assert apply(page, [{"find": "be undone.", "replace": replace}]) == (
        "After the set number of failed attempts, the device wipes itself. This cannot\nbe undone.\n\n"
        "The passcode history setting prevents users from reusing their last passcodes.\n"
        "When the value is greater than 0, the device remembers that many previous\n"
        "passcodes and rejects any attempt to reuse one of them.\n\n"
        "If a user has forgotten the passcode, send **Clear passcode** from the device's\n**Commands** tab.\n")


def test_words_spill_onto_a_line_the_page_already_had():
    # The lost-mode-dark scenario: the edit lengthens the first line of a sentence the page wraps in two.
    page = ("Supervision gives MobiVisor more control over a device. Some commands and\n"
            "policies need it: **Update OS**, **Clear passcode**, and single-app kiosk mode\n"
            "on iOS. Supervision can only be set when the device is enrolled.\n")
    new = apply(page, [{"find": "**Clear passcode**, and", "replace": "**Clear passcode**, **Lost mode**, and"}])
    assert new == ("Supervision gives MobiVisor more control over a device. Some commands and\n"
                   "policies need it: **Update OS**, **Clear passcode**, **Lost mode**, and\n"
                   "single-app kiosk mode on iOS. Supervision can only be set when the device is\n"
                   "enrolled.\n")


@pytest.mark.parametrize("find, replace, new", [
    # The next list item starts a block of its own: the spilled words stay with their item.
    ("1. Open the page.", "1. Open the page and choose a group.",
     "1. Open the page and\n   choose a group.\n2. Save.\n"),
    # Two trailing spaces are a Markdown line break: the line after it is not joined, and the break is kept.
    ("A line that ends here  ", "A longer line that ends right here  ",
     "A longer line that ends\nright here  \nand goes on.\n"),
])
def test_spilled_words_never_cross_into_another_block_or_over_a_line_break(find, replace, new):
    page = "Wrapped at twenty-two\nor so, by hand.\n\n1. Open the page.\n2. Save.\n\nA line that ends here  \nand goes on.\n"
    assert new in apply(page, [{"find": find, "replace": replace}])


def test_a_line_the_pages_wrapping_could_have_produced_is_not_broken():
    # Wrapped at 13 or more, but below 23, or "paragraph." would have fit: 15 is within that.
    page = "Short wrapped\nparagraph.\n"
    assert apply(page, [{"find": "Short", "replace": "A short"}]) == "A short wrapped\nparagraph.\n"


def test_lines_the_edit_did_not_touch_keep_their_length():
    page = "Short wrapped\nparagraph.\n\nAn untouched line that is much longer than the wrap width of this page.\n"
    new = apply(page, [{"find": "paragraph.", "replace": "paragraph, now edited."}])
    assert new == ("Short wrapped\nparagraph, now edited.\n\n"
                   "An untouched line that is much longer than the wrap width of this page.\n")


def test_a_page_that_does_not_hard_wrap_is_left_as_the_model_wrote_it():
    page = "# Kiosk Modes\n\n1. Open it.\n2. Save.\n\nLeaving kiosk mode requires the device passcode.\n"
    replace = "Leaving kiosk mode requires the exit passcode that the kiosk policy sets, not the device passcode."
    assert apply(page, [{"find": "Leaving kiosk mode requires the device passcode.", "replace": replace}]).endswith(
        f"\n\n{replace}\n")


@pytest.mark.parametrize("page, width", [
    (DEVICES, (76, 82)),                                        # "filter" did not fit after 76 characters
    ("# A heading that is long\nText.\n", None),               # a heading never wraps onto the next line
    ("1. An item\n2. Another item\n", None),                    # neither does a list item onto the next item
    ("1. An item that\n   continues here\n", (15, 24)),         # but a list item may wrap
    # Wrapped by hand: "thirty" would have fit after "Wrapped at", so the bounds clash. The limit is the width.
    ("Wrapped at\nthirty or so, and\nlater at forty-five\ncharacters.\n", (19, 19)),
    ("```\na code line\nanother\n```\n", None),                 # code is not prose
    ("% MobiVisor User Manual\n% IOTIQ\n", None),               # a Pandoc title block
    ("| a | b |\n|---|---|\n", None),
])
def test_wrap_width(page, width):
    assert wrap_width(page) == width


@pytest.mark.parametrize("page, find, message", [
    (PAGE, "", "'find' is empty"),
    (PAGE, "  \n", "'find' is empty"),
    (PAGE, "Select **Close**", "does not occur"),
    (PAGE, "**", "occurs 4 times"),
    ("the enrolled\nfilter and the enrolled  filter", "the enrolled filter", "occurs 2 times"),  # only up to whitespace
])
def test_an_edit_that_cannot_land_exactly_once_is_refused(page, find, message):
    with pytest.raises(EditError, match=message):
        apply(page, [{"find": find, "replace": "x"}])


def test_a_long_line_the_page_already_had_is_left_alone_when_the_replacement_repeats_it():
    long_line = "  See [contextually appropriate code formatting](/help/code-blocks#insert-code-formatting)."
    page = f"A paragraph that wraps\nhere, at twenty-two.\n\n* **Quote**: >\n{long_line}\n"
    new = apply(page, [{"find": f"* **Quote**: >\n{long_line}",
                        "replace": f"* **Quote**: >\n{long_line}\n\n* **Indent a list item, a new shortcut**: Ctrl + ]"}])
    assert f"\n{long_line}\n" in new
    assert new.endswith("\n* **Indent a list\n  item, a new\n  shortcut**: Ctrl + ]\n")  # the new line still wraps
