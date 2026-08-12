"""Screenshot staleness — foundation doc §5.

The finding that reshaped the project: ~60% of manual screenshots are already
produced by the E2E suite, named `<spec file>-<test name>.png`. That makes the
staleness signal fully deterministic — no model involved:

  1. an MR changes UI code
  2. the E2E suite re-captures the screenshot in CI
  3. the new capture is compared against the copy in the docs repo
  4. on difference, the affected manual pages are known exactly, via the
     filename→page index built here

This module owns steps 1 and 4 — deciding *which* images a merge request puts in
question, and *where* in the manual they appear. Step 3, the perceptual diff, is
left out on purpose: it needs the two image sets side by side in CI, which the
prototype does not have. `odiff`/`pixelmatch` with a small threshold slots in at
`impact()` when it does; byte equality is too noisy (font rendering, timing).

§5.1: the remaining ~40% are hand-captured with ad-hoc names and no test behind
them. Those need the registry, and `audit` is the CI lint that stops the
registry rotting within two releases.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

from . import manual as manual_mod

#: `<spec file>-<test name>.png` — the Cypress/Playwright convention (§5).
#:
#: Split on the *first* hyphen: the spec half is a filename stem and cannot
#: contain one, while the test half is a test title with spaces replaced by
#: underscores and routinely does — `Should_save_e-mail_settings`. An earlier
#: version required both halves to be hyphen-free and silently misfiled those
#: as hand-captured orphans. `@` is permitted in the spec half because some
#: specs are parameterised by an account name.
E2E_NAME = re.compile(r"^(?P<spec>[A-Za-z0-9_.@]+)-(?P<test>.+)\.(png|jpg|jpeg)$")

#: Hand-captured images in this manual carry a leading underscore (§5.1:
#: `_ldapSettings_1.png`, `_samsung_kiosk_Mode_1.png`). A few carry the
#: underscore *and* parse as spec-test, which is genuinely undecidable from the
#: filename. Those stay classified as orphans — conservative, because it means
#: the audit demands a registry entry until a human confirms otherwise — but
#: they are flagged so the ambiguity is visible rather than guessed at.
ORPHAN_PREFIX = "_"

#: Suffixes a spec file carries that its screenshot names do not.
SPEC_SUFFIXES = (".spec", ".cy", ".test", ".e2e")


@dataclass
class Screenshot:
    src: str
    basename: str
    kind: str  # "e2e" | "orphan"
    spec: str = ""
    test: str = ""
    ambiguous: bool = False
    uses: list[dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        out: dict[str, Any] = {
            "src": self.src,
            "basename": self.basename,
            "kind": self.kind,
            "uses": self.uses,
        }
        if self.kind == "e2e":
            out["spec"] = self.spec
            out["test"] = self.test
        if self.ambiguous:
            out["ambiguous"] = True
        return out


def _humanise(test: str) -> str:
    return test.replace("_", " ").strip()


def classify(src: str) -> Screenshot:
    basename = Path(src).name
    match = E2E_NAME.match(basename)
    if match and not basename.startswith(ORPHAN_PREFIX):
        return Screenshot(
            src=src,
            basename=basename,
            kind="e2e",
            spec=match.group("spec"),
            test=_humanise(match.group("test")),
        )
    return Screenshot(
        src=src, basename=basename, kind="orphan", ambiguous=bool(match)
    )


def build_index(manual_path: str | Path) -> dict[str, Any]:
    """Build the image→page index from the built manual."""
    parsed = manual_mod.parse(manual_path)

    screenshots: dict[str, Screenshot] = {}
    for use in parsed.images:
        shot = screenshots.get(use.src) or classify(use.src)
        shot.uses.append(use.to_dict())
        screenshots[use.src] = shot

    ordered = [screenshots[src] for src in sorted(screenshots)]
    e2e = [s for s in ordered if s.kind == "e2e"]
    return {
        "schema": "docbot.image-index/1",
        "manual": str(manual_path),
        "counts": {
            "image_references": len(parsed.images),
            "unique_images": len(ordered),
            "e2e_derived": len(e2e),
            "orphans": len(ordered) - len(e2e),
            "chapters": sum(1 for h in parsed.headings if h.level == 1),
        },
        "images": [s.to_dict() for s in ordered],
    }


def _from_dict(entry: dict[str, Any]) -> Screenshot:
    """Rebuild a Screenshot from an index entry written by `build_index`."""
    return Screenshot(
        src=entry["src"],
        basename=entry["basename"],
        kind=entry["kind"],
        spec=entry.get("spec", ""),
        test=entry.get("test", ""),
        ambiguous=entry.get("ambiguous", False),
        uses=entry.get("uses", []),
    )


def _spec_stem(path: str) -> str:
    """Reduce a changed spec path to the stem a screenshot name would carry."""
    stem = Path(path).name
    for _ in range(2):  # strips e.g. `roles_page.spec.ts` -> `roles_page`
        stem = Path(stem).stem
        if not Path(stem).suffix:
            break
    for suffix in SPEC_SUFFIXES:
        if stem.endswith(suffix):
            stem = stem[: -len(suffix)]
    return stem


def _pages_for(uses: list[dict[str, Any]]) -> list[str]:
    seen = []
    for use in uses:
        label = use.get("chapter") or "(front matter)"
        if use.get("section"):
            label = f"{label} > {use['section']}"
        if label not in seen:
            seen.append(label)
    return seen


def impact(index: dict[str, Any], changed_files: list[str]) -> dict[str, Any]:
    """Which manual pages does this merge request put in question?

    Two routes into the index, both deterministic:

      * a changed **image** is looked up directly
      * a changed **E2E spec** implicates every screenshot that spec captured

    A changed *source* file is not resolved here. Mapping source → spec needs
    coverage data the prototype does not have, and guessing it would produce
    exactly the false positives §6.2 warns against.
    """
    images = [_from_dict(img) for img in index.get("images", [])]

    by_basename = {s.basename: s for s in images}
    by_spec: dict[str, list[Screenshot]] = {}
    for shot in images:
        if shot.kind == "e2e":
            by_spec.setdefault(shot.spec.lower(), []).append(shot)

    direct: list[dict[str, Any]] = []
    via_spec: list[dict[str, Any]] = []
    unmatched_specs: list[str] = []

    for path in changed_files:
        name = Path(path).name
        if name in by_basename:
            shot = by_basename[name]
            direct.append(
                {
                    "changed_file": path,
                    "image": shot.src,
                    "kind": shot.kind,
                    "pages": _pages_for(shot.uses),
                }
            )
            continue

        stem = _spec_stem(path)
        matches = by_spec.get(stem.lower())
        if matches and Path(path).suffix in {".ts", ".js", ".tsx", ".jsx", ".py"}:
            for shot in matches:
                via_spec.append(
                    {
                        "changed_file": path,
                        "image": shot.src,
                        "test": shot.test,
                        "pages": _pages_for(shot.uses),
                    }
                )
        elif any(s in path for s in ("spec", "e2e", "cypress", "playwright")):
            unmatched_specs.append(path)

    pages = sorted({p for entry in (*direct, *via_spec) for p in entry["pages"]})
    return {
        "schema": "docbot.screenshot-impact/1",
        "changed_images": direct,
        "implicated_by_spec": via_spec,
        "specs_with_no_screenshots": sorted(set(unmatched_specs)),
        "affected_pages": pages,
        "screenshot_impact": bool(direct or via_spec),
        "note": (
            "Images implicated by a changed spec are candidates for re-capture. "
            "Confirming staleness needs the perceptual diff (§5 step 3), which "
            "requires both image sets in CI."
        ),
    }


def audit(
    index: dict[str, Any],
    registry_path: str | Path | None = None,
    images_root: str | Path | None = None,
) -> dict[str, Any]:
    """The §5.1 CI lint.

    Fails on any manual image with neither a test-derived name nor a registry
    entry. Without it "the registry rots within two releases".
    """
    images = index.get("images", [])
    orphans = [img for img in images if img["kind"] == "orphan"]

    registered: set[str] = set()
    if registry_path and Path(registry_path).is_file():
        raw = yaml.safe_load(Path(registry_path).read_text(encoding="utf-8")) or []
        registered = {Path(str(entry.get("file", ""))).name for entry in raw}

    unregistered = sorted(
        img["src"] for img in orphans if Path(img["src"]).name not in registered
    )
    # Named like an E2E capture but carrying the hand-captured prefix. Someone
    # has to look at these once; until then they are treated as orphans.
    ambiguous = sorted(img["src"] for img in orphans if img.get("ambiguous"))

    missing_on_disk: list[str] = []
    if images_root:
        root = Path(images_root)
        missing_on_disk = sorted(
            img["src"] for img in images if not (root / img["src"]).exists()
        )

    return {
        "schema": "docbot.screenshot-audit/1",
        "counts": {
            **index.get("counts", {}),
            "orphans_unregistered": len(unregistered),
            "ambiguous": len(ambiguous),
            "missing_on_disk": len(missing_on_disk),
        },
        "unregistered_orphans": unregistered,
        "ambiguous_names": ambiguous,
        "missing_on_disk": missing_on_disk,
        # Every conversion here improves both the manual and the test suite (§5.1).
        "backlog_hint": (
            f"{len(unregistered)} hand-captured image(s) have no E2E test behind them. "
            "Converting one moves it from the registry into the deterministic path."
        ),
        "ok": not unregistered and not missing_on_disk,
    }
