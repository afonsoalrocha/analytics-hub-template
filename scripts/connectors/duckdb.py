"""Local DuckDB connector. The worked example uses this and needs no credentials."""

from __future__ import annotations

import os

import duckdb
import pandas as pd

from connectors.base import Connector
from connectors.policy import Policy, apply_sql, load_policy


class DuckDBConnector(Connector):
    def __init__(
        self,
        path: str | None = None,
        *,
        read_only: bool = False,
        policy: Policy | None = None,
    ) -> None:
        self.policy = policy or load_policy()
        self.path = path or os.environ.get("DUCKDB_PATH", "data/warehouse.duckdb")
        self._connection = duckdb.connect(self.path, read_only=read_only)

    def query(self, sql: str, params: dict[str, object] | None = None) -> pd.DataFrame:
        preview = apply_sql(self.policy, sql, engine="duckdb")
        if preview is not None:
            return preview
        return self._query(sql, params)

    def _query(self, sql: str, params: dict[str, object] | None) -> pd.DataFrame:
        return self._connection.execute(sql, params or {}).df()

    def identity(self) -> dict[str, str]:
        row = self._connection.execute("select current_user() as user_name").fetchone()
        user_name = "duckdb" if row is None else str(row[0])
        return {"engine": "duckdb", "user_name": user_name, "database": str(self.path)}

    def healthcheck(self) -> bool:
        frame = self._query("select 1 as ok", None)
        return bool(frame["ok"].iloc[0] == 1)

    def close(self) -> None:
        self._connection.close()
