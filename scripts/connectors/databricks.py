"""Generic Databricks SQL connector using the Statement API."""

from __future__ import annotations

import pandas as pd

from connectors.base import Connector, ConnectorError
from connectors.env import env_float, env_int, require_env
from connectors.http import make_session, request, require_https

PENDING = frozenset({"PENDING", "RUNNING"})


class DatabricksConnector(Connector):
    def __init__(self, session: object | None = None) -> None:
        host = require_https(require_env("DATABRICKS_HOST"))
        self._host = host.rstrip("/")
        self._token = require_env("DATABRICKS_TOKEN")
        self._warehouse_id = require_env("DATABRICKS_WAREHOUSE_ID")
        self._timeout = env_float("DATABRICKS_TIMEOUT_SECONDS", 60)
        self._polls = env_int("DATABRICKS_MAX_POLLS", 10)
        self._session = session or make_session()

    def query(self, sql: str, params: dict[str, object] | None = None) -> pd.DataFrame:
        payload: dict[str, object] = {
            "warehouse_id": self._warehouse_id,
            "statement": sql,
            "wait_timeout": "50s",
            "on_wait_timeout": "CONTINUE",
            "disposition": "INLINE",
        }
        if params:
            payload["parameters"] = [
                {"name": key, "value": str(value), "type": "STRING"}
                for key, value in params.items()
            ]
        response = request(
            self._session,
            "POST",
            f"{self._host}/api/2.0/sql/statements",
            timeout=self._timeout,
            json=payload,
            headers=self._headers(),
        )
        body = _json(response)
        for _ in range(self._polls):
            state = _state(body)
            if state == "SUCCEEDED":
                return _frame(body)
            if state not in PENDING:
                raise ConnectorError(f"Databricks statement ended with state {state}.")
            statement_id = body.get("statement_id")
            if not statement_id:
                raise ConnectorError("Databricks statement is still running and returned no id.")
            response = request(
                self._session,
                "GET",
                f"{self._host}/api/2.0/sql/statements/{statement_id}",
                timeout=self._timeout,
                headers=self._headers(),
            )
            body = _json(response)
        raise ConnectorError("Databricks statement did not finish before the poll limit.")

    def healthcheck(self) -> bool:
        frame = self.query("select 1 as ok")
        return not frame.empty

    def close(self) -> None:
        close = getattr(self._session, "close", None)
        if close is not None:
            close()

    def _headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self._token}",
            "Content-Type": "application/json",
        }


def _json(response: object) -> dict[str, object]:
    status = getattr(response, "status_code", 0)
    if status >= 400:
        raise ConnectorError(f"Databricks request failed with HTTP {status}.")
    try:
        body = response.json()
    except Exception as exc:
        raise ConnectorError("Databricks returned a response that is not JSON.") from exc
    if not isinstance(body, dict):
        raise ConnectorError("Databricks returned an unexpected payload.")
    return body


def _state(body: dict[str, object]) -> str:
    status = body.get("status")
    if isinstance(status, dict):
        state = status.get("state")
        if isinstance(state, str):
            return state
    return "UNKNOWN"


def _frame(body: dict[str, object]) -> pd.DataFrame:
    manifest = body.get("manifest")
    columns: list[str] = []
    if isinstance(manifest, dict):
        schema = manifest.get("schema")
        if isinstance(schema, dict):
            raw_columns = schema.get("columns")
            if isinstance(raw_columns, list):
                columns = [
                    str(column.get("name")) for column in raw_columns if isinstance(column, dict)
                ]
    result = body.get("result")
    rows: list[list[object]] = []
    if isinstance(result, dict):
        data_array = result.get("data_array")
        if isinstance(data_array, list):
            rows = [list(row) for row in data_array]
        if result.get("external_links"):
            raise ConnectorError(
                "Databricks returned external links. Use a smaller query or raise the inline limit."
            )
    return pd.DataFrame(rows, columns=columns)
