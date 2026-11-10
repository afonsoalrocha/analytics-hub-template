"""Generic GA4 Data API connector.

GA4 is not a SQL warehouse. ``query`` takes a JSON RunReport request and
returns one row per report row.
"""

from __future__ import annotations

import json

import pandas as pd

from connectors.base import Connector, ConnectorError
from connectors.env import env_float, require_env
from connectors.google_auth import access_token
from connectors.http import make_session, request
from connectors.policy import Policy, dry_run_frame, ensure_ceiling, load_policy

READ_METHODS = frozenset({"runreport", "runpivotreport", "batchrunreports"})


class GA4Connector(Connector):
    def __init__(self, session: object | None = None, *, policy: Policy | None = None) -> None:
        self.policy = policy or load_policy()
        self._property_id = require_env("GA4_PROPERTY_ID")
        if not self._property_id.isdigit():
            raise ConnectorError("GA4_PROPERTY_ID must be the numeric property id.")
        self._timeout = env_float("GA4_TIMEOUT_SECONDS", 60)
        self._token = access_token("GA4_ACCESS_TOKEN", "BIGQUERY_ACCESS_TOKEN")
        self._session = session or make_session()

    def query(self, sql: str, params: dict[str, object] | None = None) -> pd.DataFrame:
        del params
        body = _parse_report(sql)
        _guard_report(body, allow_write=self.policy.allow_write)
        ensure_ceiling(self.policy)
        if self.policy.dry_run:
            return dry_run_frame(sql, engine="ga4", max_bytes=self.policy.max_bytes)
        return self._run(body)

    def _run(self, body: dict[str, object]) -> pd.DataFrame:
        response = request(
            self._session,
            "POST",
            f"https://analyticsdata.googleapis.com/v1beta/properties/{self._property_id}:runReport",
            timeout=self._timeout,
            json=body,
            headers={
                "Authorization": f"Bearer {self._token}",
                "Content-Type": "application/json",
            },
        )
        status = getattr(response, "status_code", 0)
        if status >= 400:
            raise ConnectorError(f"GA4 request failed with HTTP {status}.")
        try:
            payload = response.json()
        except Exception as exc:
            raise ConnectorError("GA4 returned a response that is not JSON.") from exc
        return _frame(payload)

    def identity(self) -> dict[str, str]:
        response = request(
            self._session,
            "GET",
            f"https://analyticsdata.googleapis.com/v1beta/properties/{self._property_id}/metadata",
            timeout=self._timeout,
            headers={"Authorization": f"Bearer {self._token}"},
        )
        status = getattr(response, "status_code", 0)
        if status >= 400:
            raise ConnectorError(f"GA4 identity check failed with HTTP {status}.")
        return {"engine": "ga4", "property_id": self._property_id}

    def healthcheck(self) -> bool:
        frame = self._run(
            {
                "dateRanges": [{"startDate": "7daysAgo", "endDate": "yesterday"}],
                "metrics": [{"name": "sessions"}],
                "limit": "1",
            }
        )
        return frame is not None

    def close(self) -> None:
        close = getattr(self._session, "close", None)
        if close is not None:
            close()


def _parse_report(text: str) -> dict[str, object]:
    try:
        body = json.loads(text)
    except json.JSONDecodeError as exc:
        raise ConnectorError(
            "GA4 does not accept SQL. Pass a JSON RunReport request as the query text."
        ) from exc
    if not isinstance(body, dict):
        raise ConnectorError("The GA4 request must be a JSON object.")
    return body


def _guard_report(body: dict[str, object], *, allow_write: bool) -> None:
    method = str(body.get("method", "runReport")).lower()
    if allow_write or method in READ_METHODS:
        return
    raise ConnectorError(
        "GA4 connector is read-only. Set CONNECTOR_ALLOW_WRITE=true to run a write."
    )


def _frame(payload: object) -> pd.DataFrame:
    if not isinstance(payload, dict):
        raise ConnectorError("GA4 returned an unexpected payload.")
    dimensions = _names(payload.get("dimensionHeaders"))
    metrics = _names(payload.get("metricHeaders"))
    columns = dimensions + metrics
    rows: list[dict[str, object]] = []
    raw_rows = payload.get("rows") or []
    if not isinstance(raw_rows, list):
        raise ConnectorError("GA4 returned an unexpected row list.")
    for row in raw_rows:
        if not isinstance(row, dict):
            continue
        values = _values(row.get("dimensionValues")) + _values(row.get("metricValues"))
        rows.append(dict(zip(columns, values, strict=True)))
    return pd.DataFrame(rows, columns=columns)


def _names(headers: object) -> list[str]:
    if not isinstance(headers, list):
        return []
    return [str(header.get("name")) for header in headers if isinstance(header, dict)]


def _values(cells: object) -> list[object]:
    if not isinstance(cells, list):
        return []
    return [cell.get("value") if isinstance(cell, dict) else None for cell in cells]
