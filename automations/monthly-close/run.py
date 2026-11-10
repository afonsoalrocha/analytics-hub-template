"""Append the monthly commerce mart. A failed gate does not touch the snapshot.

Zero language-model calls at runtime. This process reads the mart, runs the
gates, and writes the snapshot.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

import duckdb
import pandas as pd
import yaml

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))

from frames import normalize_monthly  # noqa: E402
from gates.checks import (  # noqa: E402
    check_grain_uniqueness,
    check_partial_month,
    check_temporal_coverage,
    check_value_domain,
)
from gates.runner import exit_code, format_report  # noqa: E402
from paths import warehouse_path  # noqa: E402
from publish import plan_append, write_frame  # noqa: E402

HERE = Path(__file__).resolve().parent


def main() -> int:
    config = yaml.safe_load((HERE / "config.yaml").read_text(encoding="utf-8"))
    relation = str(config["source_relation"])
    if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*\.[A-Za-z_][A-Za-z0-9_]*", relation):
        print("monthly-close: source_relation must be schema.table", file=sys.stderr)
        return 1
    database = warehouse_path()
    snapshot = HERE / config["snapshot_path"]
    connection = duckdb.connect(str(database), read_only=True)
    try:
        current = normalize_monthly(connection.execute(f"select * from {relation}").df())
        source_dates = [
            row[0]
            for row in connection.execute("select purchase_date from staging.stg_orders").fetchall()
        ]
    finally:
        connection.close()
    results = [
        check_grain_uniqueness(current, [config["grain"]]),
        check_value_domain(
            current,
            list(config["frozen_columns"]),
            strictly_positive=["delivered_orders", "average_ticket"],
        ),
        check_partial_month(current[config["grain"]], source_dates),
        check_temporal_coverage(source_dates, current[config["grain"]]),
    ]
    previous = pd.read_csv(snapshot) if snapshot.is_file() else None
    plan = plan_append(
        current,
        previous,
        key=config["grain"],
        columns=list(config["frozen_columns"]),
    )
    results.extend(plan.results)
    print(format_report(results))
    if exit_code(results) != 0 or not plan.write or plan.frame is None:
        print("monthly-close: snapshot left unchanged.")
        return 1
    write_frame(snapshot, plan.frame)
    print(f"monthly-close: wrote {snapshot.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
