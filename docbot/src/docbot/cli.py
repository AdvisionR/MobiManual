"""The `docbot` command line — foundation doc §8.6.

Composable subcommands, each independently testable, each emitting a JSON
artifact. Jenkins stays thin (§8.5): it collects context, runs one of these, and
archives the result. Every command here runs identically on a laptop.

    docbot gate              # is this user-facing? which areas?
    docbot screenshots ...   # which images changed / are stale?
    docbot eval              # replay a labelled corpus, score the gate

Not yet implemented, and named in §8.6 for when they are:
    docbot render-reference  # schema -> generated tables (needs the schemas)
    docbot draft             # agentic docs edit (Phase 3)
    docbot validate          # build + lint + link check (needs the sources)
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

import click

from . import docmap, evalharness, gate, screenshots
from .config import DEFAULT_MODEL, DEFAULT_PROVIDER
from .docmap import DocMapError
from .providers import ProviderError, get as get_provider


def _echo_json(data: Any) -> None:
    click.echo(json.dumps(data, indent=2, sort_keys=False))


def _write(out: str | None, data: Any) -> None:
    if out:
        path = Path(out)
        if path.parent != Path(""):
            path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(data, indent=2, sort_keys=False) + "\n", encoding="utf-8")
        click.secho(f"wrote {out}", fg="green", err=True)


def _read_changed_files(path: str) -> list[str]:
    """One path per line. `-` reads stdin, so this composes with `git diff`."""
    text = sys.stdin.read() if path == "-" else Path(path).read_text(encoding="utf-8")
    return [line.strip() for line in text.splitlines() if line.strip() and not line.startswith("#")]


@click.group()
@click.version_option(package_name="docbot")
def main() -> None:
    """MobiManual DocBot — keep the MobiVisor manual in step with the code."""


# ---------------------------------------------------------------------------
# gate
# ---------------------------------------------------------------------------


@main.command()
@click.option("--changed-files", required=True, help="File with one changed path per line, or '-' for stdin.")
@click.option("--doc-map", required=True, type=click.Path(exists=True), help="Doc map (YAML or JSON).")
@click.option("--mr", "mr_id", default="", envvar="CHANGE_ID", help="Merge request id.")
@click.option("--title", default="", envvar="CHANGE_TITLE")
@click.option("--description", default="", help="MR description. Never the diff — see gate.py.")
@click.option("--author", default="", envvar="CHANGE_AUTHOR")
@click.option("--branch", default="", envvar="CHANGE_BRANCH")
@click.option("--target", default="", envvar="CHANGE_TARGET")
@click.option("--url", default="", envvar="CHANGE_URL")
@click.option("--provider", default=DEFAULT_PROVIDER, type=click.Choice(["mistral", "fake"]))
@click.option("--model", default=DEFAULT_MODEL, show_default=True)
@click.option("--no-model", is_flag=True, help="Tier 1 only. No network call, no spend.")
@click.option("--log-dir", default=None, help="Verdict log directory (default .docbot).")
@click.option("--out", default=None, help="Write the verdict artifact here.")
@click.option("--json", "as_json", is_flag=True, help="Print the full verdict instead of a summary.")
def gate_cmd(
    changed_files: str,
    doc_map: str,
    mr_id: str,
    title: str,
    description: str,
    author: str,
    branch: str,
    target: str,
    url: str,
    provider: str,
    model: str,
    no_model: bool,
    log_dir: str | None,
    out: str | None,
    as_json: bool,
) -> None:
    """Decide whether a merge request touches the manual."""
    try:
        loaded_map = docmap.load(doc_map)
    except DocMapError as exc:
        raise click.ClickException(str(exc)) from exc

    files = _read_changed_files(changed_files)
    request = gate.MergeRequest(
        id=mr_id, title=title, description=description,
        author=author, branch=branch, target=target, url=url,
    )

    model_provider = None
    if not no_model:
        try:
            model_provider = get_provider(provider)
        except ProviderError as exc:
            raise click.ClickException(str(exc)) from exc

    verdict = gate.run(
        loaded_map, files, request,
        provider=model_provider, model=model,
        use_model=not no_model, log_dir=log_dir,
    )

    _write(out, verdict)
    if as_json:
        _echo_json(verdict)
        return

    # Human summary. This is what a reviewer reads in the build log.
    impact = verdict["doc_impact"]
    click.secho(
        f"doc_impact: {str(impact).lower()}",
        fg="yellow" if impact else "green",
        bold=True,
    )
    click.echo(f"  tier reached : {verdict['tier_reached']}")
    click.echo(f"  tier 1       : {verdict['tier1']['decision']} — {verdict['tier1']['reason']}")
    tier2 = verdict["tier2"]
    if tier2.get("ran"):
        click.echo(
            f"  tier 2       : user_facing={tier2['user_facing']} "
            f"confidence={tier2['confidence']} ({tier2['model']}, {tier2['latency_ms']}ms)"
        )
        click.echo(f"                 {tier2['reason']}")
    elif tier2.get("error"):
        click.secho(f"  tier 2       : FAILED — {tier2['error']}", fg="red")
    else:
        click.echo(f"  tier 2       : skipped — {tier2.get('skipped_because', '')}")
    if verdict["areas"]:
        click.echo(f"  areas        : {', '.join(verdict['areas'])}")
    if verdict["pages"]:
        click.echo(f"  pages        : {', '.join(verdict['pages'])}")
    if verdict["actions"]:
        click.echo(f"  actions      : {', '.join(verdict['actions'])}")
    for note in verdict["notes"]:
        click.secho(f"  note         : {note}", fg="cyan")
    click.echo(f"  logged to    : {verdict['log_path']}")


main.add_command(gate_cmd, name="gate")


# ---------------------------------------------------------------------------
# screenshots
# ---------------------------------------------------------------------------


@main.group()
def screenshots_group() -> None:
    """Screenshot staleness and the image→page index (§5)."""


main.add_command(screenshots_group, name="screenshots")


@screenshots_group.command(name="index")
@click.option("--manual", required=True, type=click.Path(exists=True), help="Built manual HTML.")
@click.option("--out", default=None)
@click.option("--json", "as_json", is_flag=True)
def screenshots_index(manual: str, out: str | None, as_json: bool) -> None:
    """Build the image→page index by parsing the built manual."""
    index = screenshots.build_index(manual)
    _write(out, index)
    if as_json:
        _echo_json(index)
        return
    counts = index["counts"]
    click.secho(f"indexed {counts['unique_images']} unique images", bold=True)
    click.echo(f"  references    : {counts['image_references']}")
    click.echo(f"  chapters      : {counts['chapters']}")
    click.echo(f"  E2E-derived   : {counts['e2e_derived']}")
    click.echo(f"  orphans       : {counts['orphans']}")


@screenshots_group.command(name="impact")
@click.option("--changed-files", required=True)
@click.option("--index", "index_path", required=True, type=click.Path(exists=True))
@click.option("--out", default=None)
@click.option("--json", "as_json", is_flag=True)
def screenshots_impact(changed_files: str, index_path: str, out: str | None, as_json: bool) -> None:
    """Which manual pages does this merge request put in question?"""
    index = json.loads(Path(index_path).read_text(encoding="utf-8"))
    result = screenshots.impact(index, _read_changed_files(changed_files))
    _write(out, result)
    if as_json:
        _echo_json(result)
        return
    if not result["screenshot_impact"]:
        click.secho("no screenshot impact", fg="green", bold=True)
    else:
        total = len(result["changed_images"]) + len(result["implicated_by_spec"])
        click.secho(f"{total} screenshot(s) in question", fg="yellow", bold=True)
        for entry in result["changed_images"]:
            click.echo(f"  changed  {entry['image']}")
        for entry in result["implicated_by_spec"]:
            click.echo(f"  re-capture  {entry['image']}  ({entry['test']})")
        click.echo("  affected pages:")
        for page in result["affected_pages"]:
            click.echo(f"    - {page}")
    for spec in result["specs_with_no_screenshots"]:
        click.secho(f"  spec with no indexed screenshot: {spec}", fg="cyan")


@screenshots_group.command(name="audit")
@click.option("--index", "index_path", required=True, type=click.Path(exists=True))
@click.option("--registry", default=None, type=click.Path(), help="Orphan registry YAML (§5.1).")
@click.option("--images-root", default=None, type=click.Path(), help="Check every image exists under here.")
@click.option("--out", default=None)
@click.option("--strict", is_flag=True, help="Exit non-zero on findings. This is the CI lint.")
def screenshots_audit(
    index_path: str, registry: str | None, images_root: str | None, out: str | None, strict: bool
) -> None:
    """Lint the image set: orphans without a registry entry, missing files."""
    index = json.loads(Path(index_path).read_text(encoding="utf-8"))
    report = screenshots.audit(index, registry, images_root)
    _write(out, report)

    counts = report["counts"]
    click.secho(
        f"{counts['orphans_unregistered']} unregistered orphan(s), "
        f"{counts['missing_on_disk']} missing on disk",
        fg="green" if report["ok"] else "yellow",
        bold=True,
    )
    for src in report["unregistered_orphans"][:20]:
        click.echo(f"  orphan   {src}")
    if len(report["unregistered_orphans"]) > 20:
        click.echo(f"  ... and {len(report['unregistered_orphans']) - 20} more")
    for src in report["missing_on_disk"][:20]:
        click.secho(f"  missing  {src}", fg="red")
    click.echo(f"  {report['backlog_hint']}")

    if strict and not report["ok"]:
        raise SystemExit(1)


# ---------------------------------------------------------------------------
# eval
# ---------------------------------------------------------------------------


@main.command(name="eval")
@click.option("--corpus", required=True, type=click.Path(exists=True), help="Labelled JSONL corpus.")
@click.option("--doc-map", required=True, type=click.Path(exists=True))
@click.option("--provider", default="fake", type=click.Choice(["mistral", "fake"]), show_default=True)
@click.option("--model", default=DEFAULT_MODEL, show_default=True)
@click.option("--no-model", is_flag=True, help="Score tier 1 alone — the deterministic baseline.")
@click.option("--out", default=None)
def eval_cmd(corpus: str, doc_map: str, provider: str, model: str, no_model: bool, out: str | None) -> None:
    """Replay a labelled corpus through the gate and score it."""
    try:
        loaded_map = docmap.load(doc_map)
    except DocMapError as exc:
        raise click.ClickException(str(exc)) from exc

    cases = evalharness.load_corpus(corpus)
    model_provider = None if no_model else get_provider(provider)
    report = evalharness.run(
        loaded_map, cases, provider=model_provider, model=model, use_model=not no_model
    )
    _write(out, report)

    click.secho(f"{report['cases']} case(s)", bold=True)
    confusion = report["confusion"]
    click.echo(
        f"  TP {confusion['TP']}  FP {confusion['FP']}  "
        f"TN {confusion['TN']}  FN {confusion['FN']}"
    )
    click.echo(f"  accuracy {report['accuracy']}  precision {report['precision']}  recall {report['recall']}")
    click.echo(f"  false-positive rate {report['false_positive_rate']} (the expensive error)")
    click.echo(f"  area exact match    {report['area_exact_match']}")
    for result in report["results"]:
        if result["outcome"] in {"FP", "FN"}:
            click.secho(
                f"  {result['outcome']}  {result['id']}: {result['reason']}", fg="yellow"
            )


if __name__ == "__main__":
    main()
