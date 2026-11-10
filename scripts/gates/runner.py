"""Turn a list of gate results into an exit code and a text report."""

from __future__ import annotations

from gates.results import GateResult


def has_block(results: list[GateResult]) -> bool:
    return any(result.blocking for result in results)


def exit_code(results: list[GateResult]) -> int:
    if has_block(results):
        return 1
    return 0


def format_report(results: list[GateResult]) -> str:
    lines = [f"[{result.state}] {result.gate}: {result.message}" for result in results]
    blocked = sum(1 for result in results if result.blocking)
    warned = sum(1 for result in results if result.state == "warn")
    lines.append(f"summary: {blocked} block, {warned} warn, {len(results)} checks")
    return "\n".join(lines)
