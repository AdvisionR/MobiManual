"""Find-and-replace edits on manual pages. Pure.

An edit names a snippet of the page and its replacement. The snippet must
occur exactly once, so an edit cannot land in the wrong place. When it does
not, the error says why, in words the model can act on. Edits apply in order,
each to the page as the previous ones left it.

Whitespace may differ: pages are hard-wrapped, and models tend to copy a
wrapped sentence onto one line. So a snippet that is not in the page as it
stands is matched again word by word, with any run of whitespace between the
words, and it still has to match exactly once.

The wrapping is restored afterwards. A model does not see where a page wraps,
and its replacement comes back as one long line, or wrapped a little wider than
the page. So on a page that hard-wraps, every line an edit wrote that is longer
than the page's own wrapping allows is broken at the page's wrap width. The
words that spill over join the next line of the same paragraph, which is broken
in turn if that makes it too long, instead of standing alone on a line of their
own. At the end of the paragraph, or before a Markdown line break, they keep a
line to themselves. A line the page already had is left as it is, even when the
replacement repeats it, unless words spill onto it; so lines before the edit,
and paragraphs after it, keep their line breaks.
"""

import re
import textwrap
from itertools import pairwise


class EditError(Exception):
    """An edit that cannot be applied."""


# Lines that start a block of their own. Never broken, and never the continuation of a wrapped line.
_BLOCK = re.compile(r"\s*(#|\||>|<|%|!\[|```|~~~|[-*+]\s|\d+[.)]\s)")
_LIST_ITEM = re.compile(r"\s*([-*+]|\d+[.)])\s+")
_FENCE = re.compile(r"\s*(```|~~~)")


def apply(text: str, edits: list[dict]) -> str:
    wrap = wrap_width(text)
    for n, edit in enumerate(edits, 1):
        find, replace = edit["find"], edit["replace"]
        if not find.strip():
            raise EditError(f"edit {n}: 'find' is empty")
        start, end = _locate(text, find, n)
        before = set(text.splitlines())
        text = text[:start] + replace + text[end:]
        if wrap:
            text = _rewrap(text, start, start + len(replace), *wrap, before)
    return text


def wrap_width(text: str) -> tuple[int, int] | None:
    """How the page hard-wraps, as (width, limit), or None if it never wraps.

    Every line that continues onto the next bounds the width the author wrapped
    at: it is at least the line's length, and less than that plus the next
    line's first word, which did not fit. width is the largest lower bound,
    where new breaks go. limit is the smallest upper bound: a longer line could
    not have come from the page's own wrapping.
    """
    lines, lower, upper, in_fence = text.splitlines(), [], [], False
    for line, following in pairwise(lines):
        if _FENCE.match(line):
            in_fence = not in_fence
            continue
        if in_fence or not line.strip() or (_BLOCK.match(line) and not _LIST_ITEM.match(line)):
            continue  # a list item may wrap; a heading, table row or image may not
        if following.strip() and not _BLOCK.match(following):
            lower.append(len(line))
            upper.append(len(line) + len(following.split()[0]))
    if not lower:
        return None
    # A page wrapped by hand may be inconsistent; the limit never goes below the width.
    return max(lower), max(min(upper), max(lower))


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


def _rewrap(text: str, start: int, end: int, width: int, limit: int, before: set[str]) -> str:
    """Break the lines that text[start:end] touches, that are longer than limit and new to the page, at width.

    A line the page already had is the author's, even when an edit's replacement repeats it. The
    words a break spills over are carried onto the next line of the paragraph, past the edit if need be.
    """
    lines = text.split("\n")
    first, last = text.count("\n", 0, start), text.count("\n", 0, max(end - 1, start))
    out, carry, n = lines[:first], "", first
    while n < len(lines) and (n <= last or carry):
        line = lines[n]
        if carry:
            line = _indent(line) + carry + " " + line.lstrip()
        elif line in before:
            out.append(line)
            n += 1
            continue
        pieces = _break(line, width, limit)
        carry = ""
        if len(pieces) > 1 and not line.endswith("  ") and n + 1 < len(lines) and _continues(lines[n + 1]):
            carry = pieces.pop().strip()
        out += pieces
        n += 1
    return "\n".join(out + lines[n:])


def _continues(line: str) -> bool:
    """Whether the line carries on the paragraph above it: neither blank nor a block of its own."""
    return bool(line.strip()) and not _BLOCK.match(line)


def _indent(line: str) -> str:
    return line[:len(line) - len(line.lstrip())]


def _break(line: str, width: int, limit: int) -> list[str]:
    line = re.sub(r"(?<=\S) $", "", line)  # one trailing space is noise; two are a Markdown line break
    if len(line) <= limit or (_BLOCK.match(line) and not _LIST_ITEM.match(line)):
        return [line]
    item = _LIST_ITEM.match(line)
    indent = " " * item.end() if item else _indent(line)
    pieces = textwrap.wrap(line, width, subsequent_indent=indent, break_long_words=False, break_on_hyphens=False)
    return [*pieces[:-1], pieces[-1] + "  "] if line.endswith("  ") else pieces
