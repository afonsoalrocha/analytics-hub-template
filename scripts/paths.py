"""Repository paths shared by the command-line tools."""

from __future__ import annotations

import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def warehouse_path() -> Path:
    configured = os.environ.get("DUCKDB_PATH")
    if configured:
        return Path(configured)
    return ROOT / "data" / "warehouse.duckdb"


def origin_path() -> Path:
    return warehouse_path().parent / "origin.json"
