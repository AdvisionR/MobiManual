"""Parse the built manual to learn where each image is used.

Foundation doc §11, Phase 1 step 3: "Build the image→page index by parsing
combined.html." This is pure string work — no model, no embeddings — and it is
what turns a changed screenshot into "chapters 3 and 7" (§5).

Parsing the *built* HTML rather than the Markdown sources is a deliberate
stopgap: the sources are open question #3 and have not arrived. The heading
anchors Pandoc emits are stable enough to index against in the meantime, and
this module is the only place that assumes HTML.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from html.parser import HTMLParser
from pathlib import Path
from typing import Any

HEADINGS = {"h1", "h2", "h3"}


@dataclass
class ImageUse:
    """One `<img>` occurrence, with the headings in force at that point."""

    src: str
    order: int
    chapter: str = ""
    chapter_anchor: str = ""
    section: str = ""
    section_anchor: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "src": self.src,
            "chapter": self.chapter,
            "chapter_anchor": self.chapter_anchor,
            "section": self.section,
            "section_anchor": self.section_anchor,
        }


@dataclass
class Heading:
    level: int
    text: str
    anchor: str


@dataclass
class Manual:
    images: list[ImageUse] = field(default_factory=list)
    headings: list[Heading] = field(default_factory=list)


class _ManualParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.manual = Manual()
        self._chapter = ("", "")
        self._section = ("", "")
        self._heading_level: int | None = None
        self._heading_anchor = ""
        self._heading_text: list[str] = []
        self._order = 0
        self._in_nav = False

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attributes = dict(attrs)
        if tag == "nav":
            # The Pandoc table of contents repeats every heading as a link. It
            # holds no images, but skipping it keeps the heading list honest.
            self._in_nav = True
        elif tag in HEADINGS and not self._in_nav:
            self._heading_level = int(tag[1])
            self._heading_anchor = attributes.get("id") or ""
            self._heading_text = []
        elif tag == "img" and not self._in_nav:
            src = attributes.get("src")
            if src:
                self._order += 1
                self.manual.images.append(
                    ImageUse(
                        src=src,
                        order=self._order,
                        chapter=self._chapter[0],
                        chapter_anchor=self._chapter[1],
                        section=self._section[0],
                        section_anchor=self._section[1],
                    )
                )

    def handle_endtag(self, tag: str) -> None:
        if tag == "nav":
            self._in_nav = False
            return
        if tag not in HEADINGS or self._heading_level is None:
            return

        # Heading text wraps across lines in the source; collapse it.
        text = re.sub(r"\s+", " ", "".join(self._heading_text)).strip()
        self.manual.headings.append(Heading(self._heading_level, text, self._heading_anchor))

        if self._heading_level == 1:
            self._chapter = (text, self._heading_anchor)
            self._section = ("", "")
        elif self._heading_level == 2:
            self._section = (text, self._heading_anchor)
        self._heading_level = None

    def handle_data(self, data: str) -> None:
        if self._heading_level is not None:
            self._heading_text.append(data)


def parse(path: str | Path) -> Manual:
    parser = _ManualParser()
    parser.feed(Path(path).read_text(encoding="utf-8", errors="replace"))
    parser.close()
    return parser.manual
