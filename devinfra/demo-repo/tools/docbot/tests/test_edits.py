import pytest

from docbot.drafting.edits import EditError, apply

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
    assert new == "Use the platform filter. The compliance filter that have been wiped.\n"


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
