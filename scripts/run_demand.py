"""Close demand 001: run the acceptance gates, then write the publication.

Block gates stop the write. Warn gates are stored in the gate report and the
command still exits 0. The CSV files are replaced only after every block gate
has passed.
"""

from __future__ import annotations

import json
import sys
from datetime import UTC, datetime
from pathlib import Path

import duckdb
import pandas as pd
import yaml

from catalog import load_cards
from frames import normalize_monthly, normalize_repurchase
from gates.checks import (
    as_date,
    check_anomalous_variation,
    check_frozen_history,
    check_grain_uniqueness,
    check_metric_status,
    check_missing_denominator_rows,
    check_partial_month,
    check_publication_metadata,
    check_reconciliation,
    check_scope_completeness,
    check_temporal_coverage,
    check_value_domain,
    complete_months,
    month_end,
)
from gates.results import GateResult, Severity
from gates.runner import exit_code, format_report
from io_utils import write_bytes_atomic, write_text_atomic
from paths import ROOT, warehouse_path

DEMAND = ROOT / "demandas" / "001-conversao-e-receita-mensal"
SNAPSHOT = ROOT / "automacoes" / "fechamento-mensal" / "snapshots" / "monthly_commerce.csv"
FROZEN_COLUMNS = ["delivered_orders", "product_revenue", "average_ticket"]


def main() -> int:
    config = yaml.safe_load((DEMAND / "config.yaml").read_text(encoding="utf-8"))
    database = warehouse_path()
    if not database.is_file():
        print("run-demand: warehouse is missing. Run make demo first.", file=sys.stderr)
        return 1
    try:
        connection = duckdb.connect(str(database), read_only=True)
        try:
            source_dates = connection.execute(
                "select purchase_date from staging.stg_orders"
            ).fetchall()
            monthly = normalize_monthly(
                connection.execute("select * from marts.mart_monthly_commerce").df()
            )
            repurchase = normalize_repurchase(
                connection.execute("select * from marts.mart_repurchase_by_cohort").df()
            )
            reconciliation = connection.execute(
                "select * from audit.audit_monthly_reconciliation"
            ).df()
            missing_items = connection.execute(
                "select count(*) from audit.audit_delivered_orders_without_items"
            ).fetchone()[0]
        finally:
            connection.close()
    except duckdb.CatalogException as exc:
        print(f"run-demand: dbt relations are missing ({exc}).", file=sys.stderr)
        return 1

    origin = _origin(database)
    metadata = _metadata(config, monthly, origin)
    results = _gates(
        config=config,
        source_dates=[row[0] for row in source_dates],
        monthly=monthly,
        repurchase=repurchase,
        reconciliation=reconciliation,
        missing_items=int(missing_items),
        metadata=metadata,
    )
    report = {
        "demand_id": config["demand_id"],
        "data_origin": origin,
        "results": [result.to_dict() for result in results],
    }
    print(format_report(results))
    gate_path = DEMAND / config["outputs"]["gate_report"]
    write_text_atomic(gate_path, json.dumps(report, indent=2) + "\n")
    if exit_code(results) != 0:
        print("run-demand: block gate failed. Publication files were left unchanged.")
        return 1
    _write_outputs(config, monthly, repurchase, metadata)
    print(f"run-demand: published {config['outputs']['monthly']}")
    return 0


def _gates(
    *,
    config: dict[str, object],
    source_dates: list[object],
    monthly: pd.DataFrame,
    repurchase: pd.DataFrame,
    reconciliation: pd.DataFrame,
    missing_items: int,
    metadata: dict[str, object],
) -> list[GateResult]:
    expected = complete_months(source_dates)
    cards = load_cards(ROOT)
    suffix = str(config["indicative_suffix"])
    exempt = ["purchase_month", "cohort_month"]
    for card in cards:
        exempt.extend(card.get("published_components") or [])
    measures = list(monthly.columns) + list(repurchase.columns)
    results = [
        check_grain_uniqueness(monthly, ["purchase_month"]),
        check_temporal_coverage(source_dates, monthly["purchase_month"]),
        check_scope_completeness(
            expected,
            monthly["purchase_month"],
            label="Closed months",
        ),
        check_partial_month(monthly["purchase_month"], source_dates),
        check_missing_denominator_rows(missing_items),
        check_value_domain(
            monthly,
            ["delivered_orders", "product_revenue", "average_ticket"],
            strictly_positive=["delivered_orders", "average_ticket"],
        ),
        _rate_domain(repurchase),
        check_reconciliation(
            reconciliation,
            left="item_gmv",
            right="payment_gmv",
            key="purchase_month",
            tolerance=float(config["reconciliation_tolerance"]),
        ),
        check_anomalous_variation(
            monthly,
            column=str(config["variation_column"]),
            key="purchase_month",
            threshold=float(config["variation_threshold"]),
        ),
        check_metric_status(
            measures,
            cards,
            indicative_suffix=suffix,
            allowed_components=exempt,
        ),
        check_publication_metadata(metadata, list(config["certified_metrics"])),
        check_grain_uniqueness(repurchase, ["cohort_month"]),
    ]
    if SNAPSHOT.is_file():
        previous = pd.read_csv(SNAPSHOT)
        results.append(
            check_frozen_history(
                previous,
                monthly,
                key="purchase_month",
                columns=FROZEN_COLUMNS,
            )
        )
    else:
        results.append(
            GateResult(
                "frozen_history",
                Severity.BLOCK,
                True,
                "No monthly snapshot yet; the automation writes the first close.",
            )
        )
    return results


def _rate_domain(repurchase: pd.DataFrame) -> GateResult:
    rates = pd.to_numeric(repurchase["repurchase_rate_indicativo"], errors="coerce")
    if bool(rates.isna().any()) or bool((rates < 0).any()) or bool((rates > 1).any()):
        return GateResult(
            "value_domain",
            Severity.BLOCK,
            False,
            "Repurchase rate must sit between 0 and 1.",
        )
    return GateResult(
        "value_domain",
        Severity.BLOCK,
        True,
        "Repurchase rate sits between 0 and 1.",
    )


def _metadata(config: dict[str, object], monthly: pd.DataFrame, origin: str) -> dict[str, object]:
    months = [as_date(value) for value in monthly["purchase_month"]]
    return {
        "demand_id": config["demand_id"],
        "data_origin": origin,
        "period_start": min(months).isoformat(),
        "period_end": month_end(max(months)).isoformat(),
        "filters": config["filters"],
        "units": config["units"],
        "loaded_at": datetime.now(UTC).replace(microsecond=0).isoformat(),
        "indicative": {
            "repurchase_rate_indicativo": {
                "unit": "ratio",
                "maturity_days": config["maturity_days"],
                "label": "Indicativo",
            }
        },
    }


def _write_outputs(
    config: dict[str, object],
    monthly: pd.DataFrame,
    repurchase: pd.DataFrame,
    metadata: dict[str, object],
) -> None:
    outputs = config["outputs"]
    assert isinstance(outputs, dict)
    write_bytes_atomic(DEMAND / outputs["monthly"], monthly.to_csv(index=False).encode("utf-8"))
    write_bytes_atomic(
        DEMAND / outputs["repurchase"],
        repurchase.to_csv(index=False).encode("utf-8"),
    )
    write_text_atomic(DEMAND / outputs["publication"], json.dumps(metadata, indent=2) + "\n")


def _origin(database: Path) -> str:
    path = database.parent / "origin.json"
    if not path.is_file():
        return "unknown"
    payload = json.loads(path.read_text(encoding="utf-8"))
    return str(payload.get("origin", "unknown"))


if __name__ == "__main__":
    sys.exit(main())
