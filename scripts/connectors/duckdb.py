"""Local DuckDB connector. The worked example uses this and needs no credentials."""

from __future__ import annotations

import os

import duckdb
import pandas as pd

from connectors.base import Connector


class DuckDBConnector(Connector):
    def __init__(self, path: str | None = None, *, read_only: bool = False) -> None:
        self.path = path or os.environ.get("DUCKDB_PATH", "data/warehouse.duckdb")
        self._connection = duckdb.connect(self.path, read_only=read_only)

    def query(self, sql: str, params: dict[str, object] | None = None) -> pd.DataFrame:
        return self._connection.execute(sql, params or {}).df()

    def healthcheck(self) -> bool:
        frame = self.query("select 1 as ok")
        return bool(frame["ok"].iloc[0] == 1)

    def close(self) -> None:
        self._connection.close()
