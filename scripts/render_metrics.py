"""Render metric cards to Markdown. The YAML card stays the source of truth."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any

from catalog import load_cards, metric_dir
from paths import ROOT


def render_card(card: dict[str, Any]) -> str:
    status = str(card["status"])
    lines = [f"# {card['name']}", "", f"- id: `{card['id']}`", f"- status: `{status}`", ""]
    if status == "indicativa":
        lines.extend(
            [
                "> **Indicativo.** Publish this figure with the `_indicativo` suffix "
                "and with its maturity window.",
                "",
            ]
        )
    elif status == "bloqueada":
        lines.extend(
            [
                "> **Bloqueada.** This metric stays unpublished.",
                "",
                str(card["block_reason"]).strip(),
                "",
            ]
        )
    formula = card["formula"]
    denominator = formula["denominator"] if formula["denominator"] is not None else "none"
    lines.extend(
        [
            "## Definition",
            "",
            str(card["definition"]).strip(),
            "",
            "## Formula",
            "",
            f"- numerator: `{formula['numerator']}`",
            f"- denominator: `{denominator}`",
            f"- aggregation: `{formula['aggregation']}`",
            "",
            "## Grain and time",
            "",
            f"- grain: `{card['grain']}`",
            f"- default date: `{card['default_date_column']}`",
            f"- maturity: {card['maturity_days']} days",
            "",
            "## Required filters",
            "",
        ]
    )
    if card["required_filters"]:
        lines.extend(f"- `{item}`" for item in card["required_filters"])
    else:
        lines.append("- None.")
    lines.extend(["", "## Allowed dimensions", ""])
    for dimension in card["allowed_dimensions"]:
        caution = str(dimension["caution"]).strip() or "No extra caution."
        lines.append(f"- `{dimension['name']}`: {caution}")
    lines.extend(
        [
            "",
            "## Reconciliation",
            "",
            str(card["reconciliation_source"]).strip(),
            "",
            "## Ownership",
            "",
            f"- owner: {card['owner']}",
            f"- decided at: {card['decided_at']}",
            "",
            "## History",
            "",
        ]
    )
    for entry in card["history"]:
        lines.append(f"- {entry['on']}: {str(entry['change']).strip()}")
    lines.append("")
    return "\n".join(lines)


def write_cards(root: Path = ROOT) -> list[Path]:
    written = []
    for card in load_cards(root):
        destination = metric_dir(root) / f"{card['id']}.md"
        destination.write_text(render_card(card), encoding="utf-8")
        written.append(destination)
    return written


def check_cards(root: Path = ROOT) -> list[str]:
    problems = []
    for card in load_cards(root):
        destination = metric_dir(root) / f"{card['id']}.md"
        expected = render_card(card)
        if not destination.is_file():
            problems.append(f"missing {destination.relative_to(root)}")
            continue
        if destination.read_text(encoding="utf-8") != expected:
            problems.append(f"stale {destination.relative_to(root)}")
    return problems


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Render metric cards to Markdown.")
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args(argv)
    if args.check:
        problems = check_cards(ROOT)
        if problems:
            print("render-metrics: rendered cards are stale.")
            for problem in problems:
                print(f"render-metrics: {problem}")
            return 1
        print("render-metrics: rendered cards match the YAML.")
        return 0
    written = write_cards(ROOT)
    for path in written:
        print(f"render-metrics: wrote {path.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
