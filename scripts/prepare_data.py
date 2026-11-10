"""Load the Olist public extract, or the synthetic fallback, into local DuckDB.

The Olist files are downloaded at runtime and are not committed. The canonical
license is CC BY-NC-SA 4.0 (https://creativecommons.org/licenses/by-nc-sa/4.0/):
NonCommercial (no commercial use) and ShareAlike. The download mirror
https://github.com/olist/work-at-olist-data declares MIT on GitHub and is used
only as the file source. Treat the CSVs under the Kaggle license, which is
separate from the MIT license of this template. The script keeps four tables.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

import duckdb
import pandas as pd
import requests

from io_utils import write_text_atomic
from paths import ROOT, origin_path, warehouse_path
from synthetic_olist import build_frames

MIRROR = "https://raw.githubusercontent.com/olist/work-at-olist-data/master/datasets"
REMOTE_FILES = {
    "olist_orders_dataset.csv": "orders",
    "olist_order_items_dataset.csv": "order_items",
    "olist_customers_dataset.csv": "customers",
    "olist_order_payments_dataset.csv": "payments",
}

ORDER_COLUMNS = [
    "order_id",
    "customer_id",
    "order_status",
    "order_purchase_timestamp",
    "order_approved_at",
    "order_delivered_carrier_date",
    "order_delivered_customer_date",
    "order_estimated_delivery_date",
]
ITEM_COLUMNS = [
    "order_id",
    "order_item_id",
    "product_id",
    "seller_id",
    "shipping_limit_date",
    "price",
    "freight_value",
]
CUSTOMER_COLUMNS = [
    "customer_id",
    "customer_unique_id",
    "customer_zip_code_prefix",
    "customer_city",
    "customer_state",
]
PAYMENT_COLUMNS = [
    "order_id",
    "payment_sequential",
    "payment_type",
    "payment_installments",
    "payment_value",
]
TIMESTAMP_COLUMNS = {
    "orders": [
        "order_purchase_timestamp",
        "order_approved_at",
        "order_delivered_carrier_date",
        "order_delivered_customer_date",
        "order_estimated_delivery_date",
    ],
    "order_items": ["shipping_limit_date"],
}


def prepare(mode: str, database: Path, raw_dir: Path) -> str:
    if mode == "synthetic":
        frames = build_frames(seed=42)
        _load(database, frames)
        _write_origin(database, "synthetic", "Seeded synthetic extract, seed 42.")
        return "synthetic"
    try:
        frames = _frames_from_olist(raw_dir)
    except (OSError, requests.RequestException, ValueError, RuntimeError) as exc:
        if mode == "olist":
            raise
        print(f"prepare-data: Olist download unavailable ({exc}). Using the synthetic seed.")
        frames = build_frames(seed=42)
        _load(database, frames)
        _write_origin(database, "synthetic", f"Fallback after download failed: {exc}")
        return "synthetic"
    _load(database, frames)
    _write_origin(
        database,
        "olist",
        "Olist public e-commerce sample via olist/work-at-olist-data.",
    )
    return "olist"


def _frames_from_olist(raw_dir: Path) -> dict[str, pd.DataFrame]:
    raw_dir.mkdir(parents=True, exist_ok=True)
    frames: dict[str, pd.DataFrame] = {}
    for filename, table in REMOTE_FILES.items():
        path = raw_dir / filename
        if not path.is_file() or path.stat().st_size < 1000:
            _download(filename, path)
        frames[table] = _normalize(table, path)
    return frames


def _download(filename: str, destination: Path) -> None:
    url = f"{MIRROR}/{filename}"
    temporary = destination.with_suffix(destination.suffix + ".partial")
    with requests.get(
        url,
        stream=True,
        timeout=(10, 180),
        verify=True,
        headers={"User-Agent": "analytics-hub-template/0.1"},
    ) as response:
        response.raise_for_status()
        with temporary.open("wb") as handle:
            for chunk in response.iter_content(chunk_size=1024 * 1024):
                if chunk:
                    handle.write(chunk)
    temporary.replace(destination)
    sample = destination.read_text(encoding="utf-8", errors="replace")[:300]
    if "order_id" not in sample and "customer_id" not in sample:
        destination.unlink(missing_ok=True)
        raise RuntimeError(f"{filename} did not look like the expected CSV.")
    print(f"prepare-data: downloaded {filename}")


def _normalize(table: str, path: Path) -> pd.DataFrame:
    frame = pd.read_csv(path)
    frame.columns = [str(column).strip().strip('"') for column in frame.columns]
    expected = {
        "orders": ORDER_COLUMNS,
        "order_items": ITEM_COLUMNS,
        "customers": CUSTOMER_COLUMNS,
        "payments": PAYMENT_COLUMNS,
    }[table]
    missing = [column for column in expected if column not in frame.columns]
    if missing:
        raise ValueError(f"{path.name} is missing columns: {', '.join(missing)}")
    selected = frame.loc[:, expected].copy()
    for column in TIMESTAMP_COLUMNS.get(table, []):
        selected[column] = pd.to_datetime(selected[column], errors="coerce")
    return selected


def _load(database: Path, frames: dict[str, pd.DataFrame]) -> None:
    database.parent.mkdir(parents=True, exist_ok=True)
    connection = duckdb.connect(str(database))
    try:
        connection.execute("create schema if not exists raw")
        for name, frame in frames.items():
            connection.register("incoming", frame)
            connection.execute(_load_sql(name))
            connection.unregister("incoming")
    finally:
        connection.close()


def _load_sql(name: str) -> str:
    if name == "orders":
        return """
            create or replace table raw.orders as
            select
                cast(order_id as varchar) as order_id,
                cast(customer_id as varchar) as customer_id,
                cast(order_status as varchar) as order_status,
                cast(order_purchase_timestamp as timestamp) as order_purchase_timestamp,
                cast(order_approved_at as timestamp) as order_approved_at,
                cast(order_delivered_carrier_date as timestamp) as order_delivered_carrier_date,
                cast(order_delivered_customer_date as timestamp) as order_delivered_customer_date,
                cast(order_estimated_delivery_date as timestamp) as order_estimated_delivery_date
            from incoming
        """
    if name == "order_items":
        return """
            create or replace table raw.order_items as
            select
                cast(order_id as varchar) as order_id,
                cast(order_item_id as integer) as order_item_id,
                cast(product_id as varchar) as product_id,
                cast(seller_id as varchar) as seller_id,
                cast(shipping_limit_date as timestamp) as shipping_limit_date,
                cast(price as double) as price,
                cast(freight_value as double) as freight_value
            from incoming
        """
    if name == "customers":
        return """
            create or replace table raw.customers as
            select
                cast(customer_id as varchar) as customer_id,
                cast(customer_unique_id as varchar) as customer_unique_id,
                cast(customer_zip_code_prefix as varchar) as customer_zip_code_prefix,
                cast(customer_city as varchar) as customer_city,
                cast(customer_state as varchar) as customer_state
            from incoming
        """
    if name == "payments":
        return """
            create or replace table raw.payments as
            select
                cast(order_id as varchar) as order_id,
                cast(payment_sequential as integer) as payment_sequential,
                cast(payment_type as varchar) as payment_type,
                cast(payment_installments as integer) as payment_installments,
                cast(payment_value as double) as payment_value
            from incoming
        """
    raise ValueError(f"Unknown table {name}")


def _write_origin(database: Path, origin: str, detail: str) -> None:
    payload = {"origin": origin, "detail": detail, "warehouse": str(database)}
    destination = database.parent / "origin.json"
    write_text_atomic(destination, json.dumps(payload, indent=2) + "\n")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Prepare the local Olist warehouse.")
    parser.add_argument(
        "--mode",
        choices=("auto", "olist", "synthetic"),
        default=os.environ.get("OLIST_SOURCE", "auto"),
    )
    parser.add_argument("--database", type=Path, default=warehouse_path())
    parser.add_argument("--raw-dir", type=Path, default=ROOT / "data" / "raw")
    args = parser.parse_args(argv)
    try:
        origin = prepare(args.mode, args.database, args.raw_dir)
    except (OSError, requests.RequestException, ValueError, RuntimeError) as exc:
        print(f"prepare-data: {exc}", file=sys.stderr)
        return 1
    print(f"prepare-data: loaded {origin} into {args.database}")
    if origin_path() != args.database.parent / "origin.json":
        print(f"prepare-data: origin file is {args.database.parent / 'origin.json'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
