"""Generic BigQuery connector over the jobs.query REST method."""

from __future__ import annotations

import pandas as pd

from connectors.base import Connector, ConnectorError
from connectors.env import env_float, env_int, require_env
from connectors.google_auth import access_token
from connectors.http import make_session, request

API = "https://bigquery.googleapis.com/bigquery/v2"


class BigQueryConnector(Connector):
    def __init__(self, session: object | None = None) -> None:
        self._project = require_env("BIGQUERY_PROJECT")
        self._timeout = env_float("BIGQUERY_TIMEOUT_SECONDS", 60)
        self._polls = env_int("BIGQUERY_MAX_POLLS", 10)
        self._token = access_token("BIGQUERY_ACCESS_TOKEN")
        self._session = session or make_session()

    def query(self, sql: str, params: dict[str, object] | None = None) -> pd.DataFrame:
        body: dict[str, object] = {
            "query": sql,
            "useLegacySql": False,
            "timeoutMs": int(self._timeout * 1000),
        }
        if params:
            body["parameterMode"] = "NAMED"
            body["queryParameters"] = [
                {
                    "name": key,
                    "parameterType": {"type": "STRING"},
                    "parameterValue": {"value": str(value)},
                }
                for key, value in params.items()
            ]
        response = request(
            self._session,
            "POST",
            f"{API}/projects/{self._project}/queries",
            timeout=self._timeout,
            json=body,
            headers=self._headers(),
        )
        payload = _json(response)
        for _ in range(self._polls):
            if payload.get("jobComplete") is True or payload.get("rows") is not None:
                return _frame(payload)
            job_id = _job_id(payload)
            if job_id is None:
                raise ConnectorError("BigQuery query did not complete and returned no job id.")
            response = request(
                self._session,
                "GET",
                f"{API}/projects/{self._project}/queries/{job_id}",
                timeout=self._timeout,
                headers=self._headers(),
            )
            payload = _json(response)
        raise ConnectorError("BigQuery query did not finish before the poll limit.")

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
        raise ConnectorError(f"BigQuery request failed with HTTP {status}.")
    try:
        body = response.json()
    except Exception as exc:
        raise ConnectorError("BigQuery returned a response that is not JSON.") from exc
    if not isinstance(body, dict):
        raise ConnectorError("BigQuery returned an unexpected payload.")
    return body


def _job_id(payload: dict[str, object]) -> str | None:
    reference = payload.get("jobReference")
    if isinstance(reference, dict) and isinstance(reference.get("jobId"), str):
        return str(reference["jobId"])
    if isinstance(payload.get("jobId"), str):
        return str(payload["jobId"])
    return None


def _frame(payload: dict[str, object]) -> pd.DataFrame:
    schema = payload.get("schema")
    columns: list[str] = []
    if isinstance(schema, dict) and isinstance(schema.get("fields"), list):
        columns = [str(field.get("name")) for field in schema["fields"] if isinstance(field, dict)]
    raw_rows = payload.get("rows")
    rows: list[list[object]] = []
    if isinstance(raw_rows, list):
        for row in raw_rows:
            if isinstance(row, dict) and isinstance(row.get("f"), list):
                rows.append(
                    [cell.get("v") if isinstance(cell, dict) else None for cell in row["f"]]
                )
    return pd.DataFrame(rows, columns=columns)
