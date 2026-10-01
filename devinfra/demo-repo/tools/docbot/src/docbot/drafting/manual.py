"""The manual as the model sees it: a table of contents, and tools to read and search it. Pure.

In the fixture, the pages are htmlDocPages from gruntfile.js, read with the
regex scripts/check-missing-doc.js uses, so the manual holds exactly the pages
the build publishes, in manual order. Build machinery (search.md, break.md) is
not listed there, so it can never be edited. Only English pages are drafted;
translations are listed as debt.

Triage reads the table of contents to know what the manual covers. Drafting
reads it too, and then reads and searches the pages it needs, so the manual
never has to fit into one prompt.
"""

import difflib
import re
from collections.abc import Collection
from dataclasses import dataclass
from pathlib import PurePosixPath

from docbot.llm import Tool
from docbot.llm.agent import Handler, ToolError, int_arg, str_arg

LANGUAGE = "en"
MAX_PAGE_LINES = 500
MAX_MATCHES = 50
MAX_LINE_CHARS = 300

_HTML_DOC_PAGES = re.compile(r"var htmlDocPages = \[([\s\S]*?)\]")
_QUOTED = re.compile(r"'([^']+)'")
_HEADING = re.compile(r"#{1,6} \S")
_FENCE = re.compile(r"(`{3,}|~{3,})")
_FRONTMATTER_TITLE = re.compile(r"\A---\n(?:(?!---\n).*\n)*?title:\s*(.+?)\s*\n(?:(?!---\n).*\n)*?---\n")

READ_PAGE = Tool(
    "read_page",
    f"Read a manual page, named as in the table of contents. At most {MAX_PAGE_LINES} lines per call; "
    "a longer page says so, and start reads on. The text is returned without line numbers, "
    "exactly as an edit's 'find' has to quote it.",
    {"type": "object",
     "properties": {"page": {"type": "string"},
                    "start": {"type": "integer", "description": "First line, from 1. Default 1."}},
     "required": ["page"]},
)
SEARCH_MANUAL = Tool(
    "search_manual",
    "Search every manual page for a regular expression, case-insensitive. Returns 'page:line: text' "
    f"for at most {MAX_MATCHES} matching lines. Use it to find every page that mentions a term.",
    {"type": "object", "properties": {"pattern": {"type": "string"}}, "required": ["pattern"]},
)


class ManualError(Exception):
    """The manual's page list cannot be read at this commit."""


def html_doc_pages(gruntfile: str) -> list[str]:
    block = _HTML_DOC_PAGES.search(gruntfile)
    if not block:
        raise ManualError("htmlDocPages not found in gruntfile.js")
    return _QUOTED.findall(block[1])


def headings(text: str) -> list[str]:
    """The page's title from its front matter, if any, then its ATX headings outside fenced code."""
    title = _FRONTMATTER_TITLE.match(text)
    found, fence = ([f"# {title[1].strip(chr(34) + chr(39))}"] if title else []), ""
    for line in text.splitlines():
        if fence:
            if line.strip().startswith(fence):
                fence = ""
        elif match := _FENCE.match(line.strip()):
            fence = match[1]
        elif _HEADING.match(line):
            found.append(line.strip().rstrip("#").strip())
    return found


@dataclass(frozen=True)
class Manual:
    pages: dict[str, str]  # page name -> text, in manual order

    def contents(self, edited: Collection[str] = ()) -> str:
        """Every page with its headings, marking the pages the merge request already edited."""
        lines = []
        for name, text in self.pages.items():
            lines.append(f"{name} (already edited in this merge request)" if name in edited else name)
            lines += [f"    {h}" for h in headings(text)]
        return "\n".join(lines)

    def tools(self) -> tuple[list[Tool], dict[str, Handler]]:
        handlers: dict[str, Handler] = {
            "read_page": lambda a: self.read_page(str_arg(a, "page"), int_arg(a, "start", 1)),
            "search_manual": lambda a: self.search(str_arg(a, "pattern")),
        }
        return [READ_PAGE, SEARCH_MANUAL], handlers

    def resolve(self, page: str) -> str:
        """The page's full name. A name without its folder or extension will do if it fits one page only."""
        if page in self.pages:
            return page
        wanted = _without_extension(page)
        matches = [name for name in self.pages
                   if _without_extension(name) == wanted or _without_extension(name).endswith("/" + wanted)]
        if len(matches) == 1:
            return matches[0]
        if matches:
            raise ToolError(f"{page!r} fits several pages: {', '.join(matches)}")
        raise ToolError(f"no page {page!r} in the table of contents{suggest(page, self.pages)}")

    def read_page(self, page: str, start: int = 1) -> str:
        page = self.resolve(page)
        lines = self.pages[page].splitlines()
        if not lines:
            return f"{page} is empty"
        start = max(start, 1)
        if start > len(lines):
            raise ToolError(f"{page} has only {len(lines)} lines")
        end = min(len(lines), start + MAX_PAGE_LINES - 1)
        more = f"; read on with start={end + 1}" if end < len(lines) else ""
        return f"{page}, lines {start}-{end} of {len(lines)}{more}:\n" + "\n".join(lines[start - 1:end])

    def search(self, pattern: str) -> str:
        try:
            regex = re.compile(pattern, re.IGNORECASE)
        except re.error as e:
            raise ToolError(f"not a valid regular expression: {e}") from e
        matches = [f"{name}:{n}: {line[:MAX_LINE_CHARS]}" for name, text in self.pages.items()
                   for n, line in enumerate(text.splitlines(), 1) if regex.search(line)]
        if not matches:
            return f"no page matches {pattern!r}"
        more = f"\n... {len(matches) - MAX_MATCHES} more matching lines; narrow the pattern" \
            if len(matches) > MAX_MATCHES else ""
        return "\n".join(matches[:MAX_MATCHES]) + more


def suggest(name: str, names) -> str:
    """'; did you mean ...?' with the closest names, or nothing."""
    close = difflib.get_close_matches(name, list(names), n=3, cutoff=0.5)
    return f"; did you mean {' or '.join(close)}?" if close else ""


def _without_extension(name: str) -> str:
    return str(PurePosixPath(name).with_suffix(""))
