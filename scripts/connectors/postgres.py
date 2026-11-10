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

ALLOWED_SSL_MODES = frozenset({"verify-full", "verify-ca"})


class PostgresConnector(Connector):
    def __init__(self) -> None:
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
        with self._connection.cursor() as cursor:
            cursor.execute(sql, params)
            if cursor.description is None:
                return pd.DataFrame()
            columns = [column.name for column in cursor.description]
            rows = cursor.fetchall()
        return pd.DataFrame(rows, columns=columns)

    def healthcheck(self) -> bool:
        frame = self.query("select 1 as ok")
        return not frame.empty and int(frame["ok"].iloc[0]) == 1

    def close(self) -> None:
        self._connection.close()


def os_sslmode() -> str:
    mode = os.environ.get("POSTGRES_SSLMODE", "verify-full").strip() or "verify-full"
    if mode not in ALLOWED_SSL_MODES:
        raise ConnectorError("POSTGRES_SSLMODE must be verify-full or verify-ca so TLS is checked.")
    return mode
