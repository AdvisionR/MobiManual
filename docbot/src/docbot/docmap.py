"""The doc map — foundation doc §6.5.

A hand-maintained file mapping code areas to manual sections. The doc calls it
"the highest-leverage cheap thing in the whole design": deterministic retrieval
beats embeddings, and stale entries surface as review friction rather than as
silent wrong edits.

Tier 1 of the three-tier gate (§6.3) is nothing but a lookup against this file.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Literal

import yaml

#: §6.4 content classification. The handling of a matched area depends entirely
#: on which of these it carries.
AreaClass = Literal["generated", "ai-drafted", "human-only", "no-doc-impact"]

VALID_CLASSES: frozenset[str] = frozenset(
    {"generated", "ai-drafted", "human-only", "no-doc-impact"}
)

#: Classes that mean "the manual may need to change". `no-doc-impact` is the
#: explicit silent case and is just as load-bearing (§6.4): it records *why* the
#: gate stays quiet so nobody rediscovers the reasoning later.
DOC_RELEVANT_CLASSES: frozenset[str] = frozenset(
    {"generated", "ai-drafted", "human-only"}
)


class DocMapError(ValueError):
    """The doc map is malformed. Always fatal: a silently wrong map is worse
    than no map, because the gate would go quiet for the wrong reason."""


@dataclass(frozen=True)
class Area:
    id: str
    code: tuple[re.Pattern[str], ...]
    pages: tuple[str, ...]
    klass: AreaClass
    description: str = ""

    def matches(self, path: str) -> bool:
        return any(pattern.search(path) for pattern in self.code)


@dataclass(frozen=True)
class DocMap:
    areas: tuple[Area, ...]
    ignore: tuple[re.Pattern[str], ...] = ()
    escalate_unmapped: bool = True
    source: Path | None = None

    def area(self, area_id: str) -> Area | None:
        return next((a for a in self.areas if a.id == area_id), None)

    @property
    def ids(self) -> tuple[str, ...]:
        return tuple(a.id for a in self.areas)

    def is_ignored(self, path: str) -> bool:
        return any(pattern.search(path) for pattern in self.ignore)


def _compile(patterns: Any, where: str) -> tuple[re.Pattern[str], ...]:
    if patterns is None:
        return ()
    if not isinstance(patterns, list):
        raise DocMapError(f"{where}: expected a list of regexes, got {type(patterns).__name__}")
    compiled = []
    for pattern in patterns:
        try:
            compiled.append(re.compile(pattern))
        except re.error as exc:
            raise DocMapError(f"{where}: bad regex {pattern!r} — {exc}") from exc
    return tuple(compiled)


def load(path: str | Path) -> DocMap:
    """Load a doc map from YAML or JSON.

    §6.5 specifies YAML. JSON is accepted because the Jenkins prototype's
    fixture map is JSON (it is matched with `jq` inside the container), and
    being able to read it unchanged makes the eventual Jenkins wiring a
    one-line swap rather than a migration.
    """
    p = Path(path)
    if not p.is_file():
        raise DocMapError(f"doc map not found: {p}")

    text = p.read_text(encoding="utf-8")
    try:
        raw = json.loads(text) if p.suffix == ".json" else yaml.safe_load(text)
    except (json.JSONDecodeError, yaml.YAMLError) as exc:
        raise DocMapError(f"{p}: could not parse — {exc}") from exc

    if not isinstance(raw, dict):
        raise DocMapError(f"{p}: top level must be a mapping")

    raw_areas = raw.get("areas")
    if not isinstance(raw_areas, list) or not raw_areas:
        raise DocMapError(f"{p}: 'areas' must be a non-empty list")

    areas: list[Area] = []
    seen: set[str] = set()
    for index, entry in enumerate(raw_areas):
        where = f"{p}: areas[{index}]"
        if not isinstance(entry, dict):
            raise DocMapError(f"{where}: expected a mapping")
        area_id = entry.get("id")
        if not area_id:
            raise DocMapError(f"{where}: missing 'id'")
        if area_id in seen:
            raise DocMapError(f"{where}: duplicate id {area_id!r}")
        seen.add(area_id)

        klass = entry.get("class")
        if klass not in VALID_CLASSES:
            raise DocMapError(
                f"{where} ({area_id}): class must be one of "
                f"{sorted(VALID_CLASSES)}, got {klass!r}"
            )

        pages = tuple(entry.get("pages") or ())
        # A cheap consistency check that catches the most common editing slip.
        if klass in DOC_RELEVANT_CLASSES and not pages:
            raise DocMapError(
                f"{where} ({area_id}): class {klass!r} but no pages listed. "
                "Use class 'no-doc-impact' if the silence is intentional."
            )

        areas.append(
            Area(
                id=area_id,
                code=_compile(entry.get("code"), f"{where} ({area_id}).code"),
                pages=pages,
                klass=klass,  # type: ignore[arg-type]
                description=entry.get("description", ""),
            )
        )

    defaults = raw.get("defaults") or {}
    if not isinstance(defaults, dict):
        raise DocMapError(f"{p}: 'defaults' must be a mapping")

    return DocMap(
        areas=tuple(areas),
        ignore=_compile(defaults.get("ignore"), f"{p}: defaults.ignore"),
        escalate_unmapped=bool(defaults.get("escalate_unmapped", True)),
        source=p,
    )


# --------------------------------------------------------------------------
# Tier 1
# --------------------------------------------------------------------------


@dataclass
class AreaHit:
    area: Area
    files: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.area.id,
            "class": self.area.klass,
            "pages": list(self.area.pages),
            "matched": sorted(self.files),
        }


@dataclass
class Tier1Result:
    """Outcome of the pure path lookup. Costs nothing and drops most merges."""

    hits: list[AreaHit]
    unmapped: list[str]
    ignored: list[str]
    escalate: bool
    reason: str

    @property
    def doc_relevant_hits(self) -> list[AreaHit]:
        return [h for h in self.hits if h.area.klass in DOC_RELEVANT_CLASSES]

    def to_dict(self) -> dict[str, Any]:
        return {
            "matched_areas": [h.to_dict() for h in self.hits],
            "unmapped_files": sorted(self.unmapped),
            "ignored_files": sorted(self.ignored),
            "decision": "escalate" if self.escalate else "drop",
            "reason": self.reason,
        }


def tier1(doc_map: DocMap, changed_files: list[str]) -> Tier1Result:
    """Match changed paths against the doc map.

    Escalates to tier 2 when a doc-relevant area is touched, or when files fall
    outside the map entirely. That second case is the important one: it is how
    a *stale doc map* becomes visible instead of silently suppressing the gate.
    Set `defaults.escalate_unmapped: false` to trade that safety net for spend.
    """
    hits: dict[str, AreaHit] = {}
    unmapped: list[str] = []
    ignored: list[str] = []

    for path in changed_files:
        matched = [a for a in doc_map.areas if a.matches(path)]
        if matched:
            for area in matched:
                hits.setdefault(area.id, AreaHit(area)).files.append(path)
        elif doc_map.is_ignored(path):
            ignored.append(path)
        else:
            unmapped.append(path)

    ordered = [hits[a.id] for a in doc_map.areas if a.id in hits]
    relevant = [h for h in ordered if h.area.klass in DOC_RELEVANT_CLASSES]

    if relevant:
        names = ", ".join(h.area.id for h in relevant)
        return Tier1Result(ordered, unmapped, ignored, True, f"doc-relevant areas touched: {names}")

    if unmapped and doc_map.escalate_unmapped:
        return Tier1Result(
            ordered,
            unmapped,
            ignored,
            True,
            f"{len(unmapped)} changed file(s) match no doc-map area — possible doc-map gap",
        )

    if ordered:
        names = ", ".join(h.area.id for h in ordered)
        return Tier1Result(ordered, unmapped, ignored, False, f"only no-doc-impact areas touched: {names}")

    return Tier1Result(ordered, unmapped, ignored, False, "no changed file maps to a doc-relevant area")
