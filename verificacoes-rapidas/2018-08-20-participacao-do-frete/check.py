"""Spot-check the freight share of the latest complete month."""

from __future__ import annotations

import os
import sys
from pathlib import Path

import duckdb

ROOT = Path(__file__).resolve().parents[2]


def main() -> int:
    database = Path(os.environ.get("DUCKDB_PATH", ROOT / "data" / "warehouse.duckdb"))
    if not database.is_file():
        print("freight-check: warehouse is missing. Run make demo first.", file=sys.stderr)
        return 1
    connection = duckdb.connect(str(database), read_only=True)
    try:
        frame = connection.execute(
            """
            select
                purchase_month,
                freight_revenue / (product_revenue + freight_revenue) as freight_share
            from audit.audit_monthly_reconciliation
            order by purchase_month desc
            limit 1
            """
        ).df()
    finally:
        connection.close()
    if frame.empty:
        print("freight-check: reconciliation view is empty.", file=sys.stderr)
        return 1
    share = float(frame["freight_share"].iloc[0])
    month = str(frame["purchase_month"].iloc[0])[:10]
    if not 0 < share < 1:
        print(f"freight-check: share {share} is outside (0, 1).", file=sys.stderr)
        return 1
    print(f"Result: in {month} freight is {share:.1%} of price plus freight.")
    print("Conclusion: freight belongs with the ticket; this check does not become a demand.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
