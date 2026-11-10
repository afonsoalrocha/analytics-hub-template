"""Generic Postgres connector.

``POSTGRES_SSLMODE`` defaults to ``verify-full``. Modes that skip certificate
verification are refused.
"""

from __future__ import annotations

import os

import pandas as pd
import psycopg

from connectors.base import Connector, ConnectorError
from connectors.env import env_int, require_env
from connectors.policy import Policy, apply_sql, load_policy

ALLOWED_SSL_MODES = frozenset({"verify-full", "verify-ca"})


class PostgresConnector(Connector):
    def __init__(self, policy: Policy | None = None) -> None:
        self.policy = policy or load_policy()
        sslmode = os_sslmode()
        timeout = env_int("POSTGRES_CONNECT_TIMEOUT_SECONDS", 10)
        self._connection = psycopg.connect(
            host=require_env("POSTGRES_HOST"),
            port=env_int("POSTGRES_PORT", 5432),
            dbname=require_env("POSTGRES_DB"),
            user=require_env("POSTGRES_USER"),
            password=require_env("POSTGRES_PASSWORD"),
            sslmode=sslmode,
            connect_timeout=timeout,
        )

    def query(self, sql: str, params: dict[str, object] | None = None) -> pd.DataFrame:
        preview = apply_sql(self.policy, sql, engine="postgres")
        if preview is not None:
            return preview
        return self._query(sql, params)

    def _query(self, sql: str, params: dict[str, object] | None) -> pd.DataFrame:
        with self._connection.cursor() as cursor:
            cursor.execute(sql, params)
            if cursor.description is None:
                return pd.DataFrame()
            columns = [column.name for column in cursor.description]
            rows = cursor.fetchall()
        return pd.DataFrame(rows, columns=columns)

    def identity(self) -> dict[str, str]:
        frame = self._query(
            "select current_user as user_name, current_database() as database_name",
            None,
        )
        return {
            "engine": "postgres",
            "user_name": str(frame["user_name"].iloc[0]),
            "database_name": str(frame["database_name"].iloc[0]),
        }

    def healthcheck(self) -> bool:
        frame = self._query("select 1 as ok", None)
        return not frame.empty and int(frame["ok"].iloc[0]) == 1

    def close(self) -> None:
        self._connection.close()


def os_sslmode() -> str:
    mode = os.environ.get("POSTGRES_SSLMODE", "verify-full").strip() or "verify-full"
    if mode not in ALLOWED_SSL_MODES:
        raise ConnectorError("POSTGRES_SSLMODE must be verify-full or verify-ca so TLS is checked.")
    return mode
