"""Label a request complete, partial, or blocked before it is closed.

``complete`` means the documents agree and no gate warning or block is on disk.
``partial`` means the documents can close after the human records a warning.
``blocked`` means the close stops. Closing a paused request is blocked: a
paused request cannot carry an outcome. A missing gate report is normal in a
fresh checkout, because publication files stay out of git.

The label is a closing outcome. It is not a lifecycle status.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path

import yaml

from paths import ROOT
from registry import load_registry

README_HEADINGS = (
    "Question",
    "Requester",
    "Decision this supports",
    "Metrics",
    "Grain",
    "Period",
    "Out of scope",
    "Acceptance criteria",
    "Status",
)
INSIGHT_HEADINGS = (
    "Recommendation",
    "Context",
    "Findings",
    "Recommendations",
    "Files",
    "Revision log",
)
_LINK = re.compile(r"\[[^\]]+\]\(([^)]+)\)")


@dataclass(frozen=True)
class Completion:
    label: str
    notes: tuple[str, ...]


def assess(root: Path, request_id: str, *, closing: bool) -> Completion:
    blocked: list[str] = []
    partial: list[str] = []

    def block(message: str) -> None:
        blocked.append(message)

    def warn(message: str) -> None:
        partial.append(message)

    try:
        document = load_registry(root)
    except (OSError, yaml.YAMLError, ValueError) as exc:
        return Completion("blocked", (str(exc),))

    entry = _entry(document, request_id)
    if entry is None:
        return Completion("blocked", (f"{request_id}: missing from registry.yaml.",))
    if closing and str(entry.get("status")) == "paused":
        return Completion(
            "blocked",
            (f"{request_id}: a paused request cannot carry an outcome.",),
        )

    slug = str(entry.get("slug"))
    folder = root / "requests" / f"{request_id}-{slug}"
    if root / str(entry.get("path")) != folder:
        block(f"{request_id}: path must be requests/{request_id}-{slug}.")
    if not folder.is_dir():
        block(f"{request_id}: folder is missing.")
        return Completion("blocked", tuple(blocked))

    config = _config(folder, request_id, block)
    _readme(folder, request_id, block)
    _insights(
        folder,
        request_id,
        status=str(entry.get("status")),
        closing=closing,
        block=block,
        warn=warn,
    )
    _gate_report(folder, request_id, config, block, warn)

    if blocked:
        return Completion("blocked", tuple(blocked + partial))
    if partial:
        return Completion("partial", tuple(partial))
    return Completion("complete", ())


def _entry(document: dict[str, object], request_id: str) -> dict[str, object] | None:
    requests = document.get("requests")
    if not isinstance(requests, list):
        return None
    for item in requests:
        if isinstance(item, dict) and str(item.get("id")) == request_id:
            return item
    return None


def _config(folder: Path, request_id: str, block) -> dict[str, object] | None:
    path = folder / "config.yaml"
    if not path.is_file():
        block(f"{request_id}: config.yaml is missing.")
        return None
    try:
        config = yaml.safe_load(path.read_text(encoding="utf-8"))
    except yaml.YAMLError as exc:
        block(f"{request_id}: config.yaml is not valid YAML ({exc}).")
        return None
    if not isinstance(config, dict):
        block(f"{request_id}: config.yaml must be a mapping.")
        return None
    if str(config.get("request_id")) != request_id:
        block(f"{request_id}: config.yaml request_id does not match.")
    return config


def _readme(folder: Path, request_id: str, block) -> None:
    path = folder / "README.md"
    if not path.is_file():
        block(f"{request_id}: README.md is missing.")
        return
    text = path.read_text(encoding="utf-8")
    for heading in README_HEADINGS:
        if f"## {heading}" not in text:
            block(f"{request_id}: README is missing heading {heading}.")
    for target in _relative_links(text):
        if not (path.parent / target).resolve().is_file():
            block(f"{request_id}: README links to missing {target}.")


def _insights(folder: Path, request_id: str, *, status: str, closing: bool, block, warn) -> None:
    hard = closing or status == "closed"
    path = folder / "insights.md"
    if not path.is_file():
        _severity(f"{request_id}: insights.md is missing.", hard=hard, block=block, warn=warn)
        return
    text = path.read_text(encoding="utf-8")
    for heading in INSIGHT_HEADINGS:
        if f"## {heading}" not in text:
            _severity(
                f"{request_id}: insights.md is missing heading {heading}.",
                hard=hard,
                block=block,
                warn=warn,
            )
    revision = text.find("## Revision log")
    if revision >= 0 and "### " not in text[revision:]:
        _severity(
            f"{request_id}: revision log has no dated entry.",
            hard=hard,
            block=block,
            warn=warn,
        )


def _gate_report(
    folder: Path,
    request_id: str,
    config: dict[str, object] | None,
    block,
    warn,
) -> None:
    relative = "outputs/gate_report.json"
    if isinstance(config, dict):
        outputs = config.get("outputs")
        if isinstance(outputs, dict) and outputs.get("gate_report"):
            relative = str(outputs["gate_report"])
    path = folder / relative
    if not path.is_file():
        return
    try:
        report = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        block(f"{request_id}: gate report is not valid JSON.")
        return
    results = report.get("results") if isinstance(report, dict) else None
    if not isinstance(results, list):
        block(f"{request_id}: gate report has no results list.")
        return
    states = [item.get("state") for item in results if isinstance(item, dict)]
    if any(state == "block" for state in states):
        block(f"{request_id}: a gate report contains a block.")
    elif any(state == "warn" for state in states):
        warn(f"{request_id}: a gate report contains a warning.")


def _severity(message: str, *, hard: bool, block, warn) -> None:
    if hard:
        block(message)
    else:
        warn(message)


def _relative_links(text: str) -> list[str]:
    found: list[str] = []
    for match in _LINK.finditer(text):
        target = match.group(1).strip().split("#", 1)[0].strip()
        if not target or "://" in target or target.startswith("mailto:"):
            continue
        found.append(target)
    return found


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Label a request before closing it.")
    parser.add_argument("--request", required=True)
    parser.add_argument("--root", type=Path, default=ROOT)
    args = parser.parse_args(argv)
    result = assess(args.root, args.request, closing=True)
    print(result.label)
    for note in result.notes:
        print(f"- {note}")
    if result.label == "complete":
        return 0
    if result.label == "partial":
        return 2
    return 1


if __name__ == "__main__":
    sys.exit(main())
