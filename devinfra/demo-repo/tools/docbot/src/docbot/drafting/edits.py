"""Find-and-replace edits on manual pages. Pure.

An edit names a snippet of the page and its replacement. The snippet must
occur exactly once, so an edit cannot land in the wrong place. When it does
not, the error says why, in words the model can act on. Edits apply in order,
each to the page as the previous ones left it.

Whitespace may differ: pages are hard-wrapped, and models tend to copy a
wrapped sentence onto one line. So a snippet that is not in the page as it
stands is matched again word by word, with any run of whitespace between the
words, and it still has to match exactly once.
"""

import re


class EditError(Exception):
    """An edit that cannot be applied."""


def apply(text: str, edits: list[dict]) -> str:
    for n, edit in enumerate(edits, 1):
        find, replace = edit["find"], edit["replace"]
        if not find.strip():
            raise EditError(f"edit {n}: 'find' is empty")
        start, end = _locate(text, find, n)
        text = text[:start] + replace + text[end:]
    return text


def _locate(text: str, find: str, n: int) -> tuple[int, int]:
    count = text.count(find)
    if count == 1:
        start = text.index(find)
        return start, start + len(find)
    if count == 0:
        matches = list(re.finditer(r"\s+".join(re.escape(word) for word in find.split()), text))
        if len(matches) == 1:
            return matches[0].span()
        count = len(matches)
    if count == 0:
        raise EditError(f"edit {n}: 'find' does not occur in the page. Copy it exactly from the page: {find!r}")
    raise EditError(f"edit {n}: 'find' occurs {count} times. Include more of the surrounding text: {find!r}")
