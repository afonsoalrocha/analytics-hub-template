"""Pure acceptance checks.

Each function returns one ``GateResult``. Integrity checks use severity
``block``. Anomaly checks use severity ``warn``. Nothing here writes a file.
"""

from __future__ import annotations

import calendar
from collections import defaultdict
from collections.abc import Iterable
from datetime import date, datetime, timedelta

import pandas as pd

from gates.results import GateResult, Severity


def as_date(value: object) -> date:
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    if isinstance(value, pd.Timestamp):
        return value.date()
    text = str(value)[:10]
    return date.fromisoformat(text)


def month_start(value: object) -> date:
    current = as_date(value)
    return current.replace(day=1)


def month_end(value: object) -> date:
    start = month_start(value)
    last_day = calendar.monthrange(start.year, start.month)[1]
    return date(start.year, start.month, last_day)


def complete_months(source_dates: Iterable[object]) -> list[date]:
    """Return months that are closed and have a source row on every day.

    A month that is still open, or that is missing a day, stays out. The
    caller publishes those months only. A missing month is left absent; it
    is not written as a zero.
    """

    days = {as_date(item) for item in source_dates}
    if not days:
        return []
    latest = max(days)
    by_month: dict[date, set[date]] = defaultdict(set)
    for item in days:
        by_month[month_start(item)].add(item)
    ready: list[date] = []
    for start in sorted(by_month):
        end = month_end(start)
        if end > latest:
            continue
        expected = {start + timedelta(days=offset) for offset in range((end - start).days + 1)}
        if by_month[start] == expected:
            ready.append(start)
    return ready


def check_grain_uniqueness(frame: pd.DataFrame, grain: list[str]) -> GateResult:
    if frame.empty:
        return GateResult("grain_uniqueness", Severity.BLOCK, False, "The output has no rows.")
    missing = [column for column in grain if column not in frame.columns]
    if missing:
        return GateResult(
            "grain_uniqueness",
            Severity.BLOCK,
            False,
            "Grain columns are missing: " + ", ".join(missing) + ".",
        )
    duplicated = frame.duplicated(grain, keep=False)
    if bool(duplicated.any()):
        sample = frame.loc[duplicated, grain].head(5).to_dict(orient="records")
        return GateResult(
            "grain_uniqueness",
            Severity.BLOCK,
            False,
            f"Duplicate grain rows: {sample}.",
        )
    return GateResult(
        "grain_uniqueness",
        Severity.BLOCK,
        True,
        f"Grain {grain} is unique across {len(frame)} rows.",
    )


def check_temporal_coverage(
    source_dates: Iterable[object],
    published_months: Iterable[object],
) -> GateResult:
    days = {as_date(item) for item in source_dates}
    gaps: list[str] = []
    months = [month_start(item) for item in published_months]
    for start in months:
        end = month_end(start)
        expected = {start + timedelta(days=offset) for offset in range((end - start).days + 1)}
        missing_days = sorted(expected - days)
        if missing_days:
            gaps.append(f"{start.isoformat()} missing {len(missing_days)} days")
    if gaps:
        return GateResult(
            "temporal_coverage",
            Severity.BLOCK,
            False,
            "Published months are missing source days: " + "; ".join(gaps) + ".",
        )
    return GateResult(
        "temporal_coverage",
        Severity.BLOCK,
        True,
        f"Every day of {len(months)} published months is present in the source.",
    )


def check_scope_completeness(
    expected: Iterable[object],
    actual: Iterable[object],
    *,
    label: str,
) -> GateResult:
    expected_keys = {month_start(item) for item in expected}
    actual_keys = {month_start(item) for item in actual}
    missing = sorted(expected_keys - actual_keys)
    extra = sorted(actual_keys - expected_keys)
    if missing or extra:
        parts: list[str] = []
        if missing:
            rendered = ", ".join(item.isoformat() for item in missing)
            parts.append(f"missing, left unpublished: {rendered}")
        if extra:
            rendered = ", ".join(item.isoformat() for item in extra)
            parts.append(f"unexpected: {rendered}")
        return GateResult(
            "scope_completeness",
            Severity.BLOCK,
            False,
            f"{label}: " + "; ".join(parts) + ".",
        )
    return GateResult(
        "scope_completeness",
        Severity.BLOCK,
        True,
        f"{label}: {len(expected_keys)} expected keys are present.",
    )


def check_value_domain(
    frame: pd.DataFrame,
    columns: list[str],
    *,
    strictly_positive: list[str] | None = None,
) -> GateResult:
    positive = set(strictly_positive or [])
    problems: list[str] = []
    for column in columns:
        if column not in frame.columns:
            problems.append(f"{column} is missing")
            continue
        series = pd.to_numeric(frame[column], errors="coerce")
        if bool(series.isna().any()):
            problems.append(f"{column} has a null")
            continue
        if bool((series < 0).any()):
            problems.append(f"{column} is negative")
        elif column in positive and bool((series <= 0).any()):
            problems.append(f"{column} has a zero denominator")
    if problems:
        return GateResult(
            "value_domain",
            Severity.BLOCK,
            False,
            "Counts and amounts must be present and non-negative: " + "; ".join(problems) + ".",
        )
    return GateResult(
        "value_domain",
        Severity.BLOCK,
        True,
        "Counts and amounts are present and non-negative.",
    )


def check_partial_month(
    published_months: Iterable[object],
    source_dates: Iterable[object],
) -> GateResult:
    days = [as_date(item) for item in source_dates]
    if not days:
        return GateResult("partial_month", Severity.BLOCK, False, "The source has no dates.")
    latest = max(days)
    day_set = set(days)
    rejected: list[str] = []
    for start in [month_start(item) for item in published_months]:
        end = month_end(start)
        expected = {start + timedelta(days=offset) for offset in range((end - start).days + 1)}
        if end > latest or not expected.issubset(day_set):
            rejected.append(start.isoformat())
    if rejected:
        return GateResult(
            "partial_month",
            Severity.BLOCK,
            False,
            "Open or incomplete months stay unpublished: " + ", ".join(rejected) + ".",
        )
    return GateResult(
        "partial_month",
        Severity.BLOCK,
        True,
        "Every published month is closed and complete.",
    )


def check_reconciliation(
    frame: pd.DataFrame,
    *,
    left: str,
    right: str,
    key: str,
    tolerance: float,
) -> GateResult:
    if frame.empty:
        return GateResult("reconciliation", Severity.WARN, False, "Reconciliation frame is empty.")
    breaches: list[str] = []
    for record in frame.to_dict(orient="records"):
        base = record.get(left)
        other = record.get(right)
        label = as_date(record[key]).isoformat()
        if pd.isna(base) or pd.isna(other):
            breaches.append(f"{label} is missing one side")
            continue
        base_value = float(base)
        other_value = float(other)
        if base_value == 0:
            relative = 0.0 if other_value == 0 else 1.0
        else:
            relative = abs(other_value - base_value) / abs(base_value)
        if relative > tolerance:
            breaches.append(f"{label} differs by {relative:.2%} (limit {tolerance:.2%})")
    if breaches:
        return GateResult(
            "reconciliation",
            Severity.WARN,
            False,
            "Independent source is outside tolerance: " + "; ".join(breaches) + ".",
        )
    return GateResult(
        "reconciliation",
        Severity.WARN,
        True,
        f"Independent source stays within {tolerance:.2%} on {len(frame)} periods.",
    )


def check_anomalous_variation(
    frame: pd.DataFrame,
    *,
    column: str,
    key: str,
    threshold: float,
) -> GateResult:
    ordered = frame.copy()
    ordered["_key"] = ordered[key].map(as_date)
    ordered = ordered.sort_values("_key")
    values = [float(value) for value in ordered[column].tolist()]
    keys = ordered["_key"].tolist()
    breaches: list[str] = []
    for index in range(1, len(values)):
        previous = values[index - 1]
        current = values[index]
        if previous == 0:
            continue
        change = abs(current - previous) / abs(previous)
        if change > threshold:
            breaches.append(
                f"{keys[index].isoformat()} moved {change:.1%} versus {keys[index - 1].isoformat()}"
            )
    if breaches:
        return GateResult(
            "anomalous_variation",
            Severity.WARN,
            False,
            f"Movement above {threshold:.0%} versus the previous period: "
            + "; ".join(breaches)
            + ".",
        )
    return GateResult(
        "anomalous_variation",
        Severity.WARN,
        True,
        f"No period moves more than {threshold:.0%} versus the previous one.",
    )


def _normalized_records(
    frame: pd.DataFrame,
    key: str,
    columns: list[str],
) -> dict[str, tuple[float, ...]]:
    records: dict[str, tuple[float, ...]] = {}
    for record in frame.to_dict(orient="records"):
        grain = as_date(record[key]).isoformat()
        values: list[float] = []
        for column in columns:
            number = float(record[column])
            values.append(round(number, 2))
        records[grain] = tuple(values)
    return records


def check_frozen_history(
    previous: pd.DataFrame | None,
    current: pd.DataFrame,
    *,
    key: str,
    columns: list[str],
) -> GateResult:
    if previous is None or previous.empty:
        return GateResult(
            "frozen_history",
            Severity.BLOCK,
            True,
            "No prior snapshot; this is the first close.",
        )
    before = _normalized_records(previous, key, columns)
    after = _normalized_records(current, key, columns)
    changed = []
    for grain, values in before.items():
        if grain not in after:
            changed.append(f"{grain} was removed")
        elif after[grain] != values:
            changed.append(f"{grain} changed")
    if changed:
        return GateResult(
            "frozen_history",
            Severity.BLOCK,
            False,
            "A new write must leave delivered periods unchanged: " + "; ".join(changed) + ".",
        )
    return GateResult(
        "frozen_history",
        Severity.BLOCK,
        True,
        f"History for {len(before)} delivered periods is unchanged.",
    )


def check_metric_status(
    measure_columns: Iterable[str],
    catalog: list[dict[str, object]],
    *,
    indicative_suffix: str,
    allowed_components: Iterable[str] = (),
) -> GateResult:
    by_id = {str(item["id"]): item for item in catalog}
    components = set(allowed_components)
    problems: list[str] = []
    for column in measure_columns:
        if column in components:
            continue
        if column.endswith(indicative_suffix):
            metric_id = column[: -len(indicative_suffix)]
            card = by_id.get(metric_id)
            if card is None:
                problems.append(f"{column} has no metric card")
                continue
            if card["status"] != "indicativa":
                problems.append(f"{column} uses the indicative suffix but is {card['status']}")
            continue
        card = by_id.get(column)
        if card is None:
            problems.append(f"{column} has no metric card")
            continue
        status = card["status"]
        if status == "bloqueada":
            problems.append(f"{column} is blocked and stays unpublished")
        elif status == "indicativa":
            problems.append(
                f"{column} is indicative and is published as {column}{indicative_suffix}"
            )
    blocked_ids = [metric_id for metric_id, card in by_id.items() if card["status"] == "bloqueada"]
    leaked = [metric_id for metric_id in blocked_ids if metric_id in set(measure_columns)]
    for metric_id in leaked:
        message = f"{metric_id} is blocked and stays unpublished"
        if message not in problems:
            problems.append(message)
    if problems:
        return GateResult("metric_status", Severity.BLOCK, False, "; ".join(problems) + ".")
    return GateResult(
        "metric_status",
        Severity.BLOCK,
        True,
        "Every published measure has a status. Blocked metrics are absent.",
    )


def check_publication_metadata(
    metadata: dict[str, object],
    certified_ids: list[str],
) -> GateResult:
    required = ["period_start", "period_end", "filters", "units", "loaded_at"]
    missing = [key for key in required if not metadata.get(key)]
    units = metadata.get("units")
    unit_map = units if isinstance(units, dict) else {}
    unit_gaps = [metric_id for metric_id in certified_ids if not unit_map.get(metric_id)]
    if missing or unit_gaps:
        return GateResult(
            "publication_metadata",
            Severity.BLOCK,
            False,
            "A certified answer shows period, filters, unit, and load time. "
            f"Missing fields: {missing or 'none'}. Missing units: {unit_gaps or 'none'}.",
        )
    return GateResult(
        "publication_metadata",
        Severity.BLOCK,
        True,
        "Certified output records period, filters, units, and load time.",
    )


def check_missing_denominator_rows(row_count: int) -> GateResult:
    if row_count > 0:
        return GateResult(
            "scope_completeness",
            Severity.BLOCK,
            False,
            f"{row_count} delivered orders have no items. Absence stays unpublished "
            "and is not filled with zero.",
        )
    return GateResult(
        "scope_completeness",
        Severity.BLOCK,
        True,
        "Every delivered order in scope has item rows.",
    )
