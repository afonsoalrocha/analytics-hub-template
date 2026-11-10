"""Append-only publication with a frozen history check.

Validation finishes before any byte is replaced. A block leaves the previous
snapshot where it was.
"""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from gates.checks import check_frozen_history
from gates.results import GateResult
from io_utils import write_bytes_atomic


@dataclass(frozen=True)
class PublishPlan:
    frame: pd.DataFrame | None
    results: list[GateResult]
    write: bool


def plan_append(
    current: pd.DataFrame,
    previous: pd.DataFrame | None,
    *,
    key: str,
    columns: list[str],
) -> PublishPlan:
    frozen = check_frozen_history(previous, current, key=key, columns=columns)
    if frozen.blocking:
        return PublishPlan(frame=None, results=[frozen], write=False)
    if previous is None or previous.empty:
        combined = current.sort_values(key).reset_index(drop=True)
        return PublishPlan(frame=combined, results=[frozen], write=True)
    previous_keys = set(previous[key].map(_key))
    additions = current.loc[~current[key].map(_key).isin(previous_keys)].copy()
    combined = pd.concat([previous, additions], ignore_index=True)
    combined = combined.sort_values(key).reset_index(drop=True)
    return PublishPlan(frame=combined, results=[frozen], write=True)


def write_frame(path: object, frame: pd.DataFrame) -> None:
    from pathlib import Path

    destination = Path(path)
    payload = frame.to_csv(index=False).encode("utf-8")
    write_bytes_atomic(destination, payload)


def _key(value: object) -> str:
    from gates.checks import as_date

    return as_date(value).isoformat()
