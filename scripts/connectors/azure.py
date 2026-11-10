"""Generic Azure Blob and Azure DevOps connectors.

Blob storage has no SQL endpoint: pass the blob path to ``query``. Azure
DevOps accepts a WIQL statement, which is shaped like a select.
"""

from __future__ import annotations

import base64
from collections.abc import Mapping
from io import BytesIO
from urllib.parse import quote

import pandas as pd

from connectors.base import Connector, ConnectorError
from connectors.env import env_float, require_env
from connectors.http import make_session, request
from connectors.policy import Policy, apply_sql, dry_run_frame, ensure_ceiling, load_policy


class AzureBlobConnector(Connector):
    def __init__(self, session: object | None = None, *, policy: Policy | None = None) -> None:
        self.policy = policy or load_policy()
        account = require_env("AZURE_STORAGE_ACCOUNT")
        if not account.replace("-", "").isalnum():
            raise ConnectorError("AZURE_STORAGE_ACCOUNT must be the account name, not a URL.")
        self._account = account
        self._container = require_env("AZURE_STORAGE_CONTAINER")
        token = require_env("AZURE_STORAGE_SAS_TOKEN")
        self._sas = token[1:] if token.startswith("?") else token
        self._timeout = env_float("AZURE_TIMEOUT_SECONDS", 60)
        self._session = session or make_session()

    def query(self, sql: str, params: dict[str, object] | None = None) -> pd.DataFrame:
        raw_path = str((params or {}).get("path", sql)).strip()
        _guard_blob_path(raw_path)
        ensure_ceiling(self.policy)
        if self.policy.dry_run:
            return dry_run_frame(raw_path, engine="azure_blob", max_bytes=self.policy.max_bytes)
        url = (
            f"https://{self._account}.blob.core.windows.net/"
            f"{quote(self._container)}/{quote(raw_path)}?{self._sas}"
        )
        response = request(self._session, "GET", url, timeout=self._timeout)
        status = getattr(response, "status_code", 0)
        if status >= 400:
            raise ConnectorError(f"Azure Blob request failed with HTTP {status}.")
        _guard_content_length(response, self.policy.max_bytes)
        payload = getattr(response, "content", b"")
        return pd.read_csv(BytesIO(payload))

    def identity(self) -> dict[str, str]:
        url = (
            f"https://{self._account}.blob.core.windows.net/{quote(self._container)}"
            f"?restype=container&{self._sas}"
        )
        response = request(self._session, "GET", url, timeout=self._timeout)
        status = getattr(response, "status_code", 0)
        if status >= 400:
            raise ConnectorError(f"Azure Blob identity check failed with HTTP {status}.")
        return {
            "engine": "azure_blob",
            "account": self._account,
            "container": self._container,
        }

    def healthcheck(self) -> bool:
        url = (
            f"https://{self._account}.blob.core.windows.net/{quote(self._container)}"
            f"?restype=container&comp=list&maxresults=1&{self._sas}"
        )
        response = request(self._session, "GET", url, timeout=self._timeout)
        return getattr(response, "status_code", 0) < 400

    def close(self) -> None:
        close = getattr(self._session, "close", None)
        if close is not None:
            close()


class AzureDevOpsConnector(Connector):
    def __init__(self, session: object | None = None, *, policy: Policy | None = None) -> None:
        self.policy = policy or load_policy()
        organization = require_env("AZURE_DEVOPS_ORG")
        project = require_env("AZURE_DEVOPS_PROJECT")
        if "/" in organization or "/" in project:
            raise ConnectorError(
                "AZURE_DEVOPS_ORG and AZURE_DEVOPS_PROJECT are single path segments."
            )
        self._organization = organization
        self._project = project
        self._pat = require_env("AZURE_DEVOPS_PAT")
        self._timeout = env_float("AZURE_TIMEOUT_SECONDS", 60)
        self._session = session or make_session()

    def query(self, sql: str, params: dict[str, object] | None = None) -> pd.DataFrame:
        del params
        preview = apply_sql(self.policy, sql, engine="azure_devops")
        if preview is not None:
            return preview
        return self._wiql(sql)

    def _wiql(self, sql: str) -> pd.DataFrame:
        token = base64.b64encode(f":{self._pat}".encode()).decode("ascii")
        url = (
            f"https://dev.azure.com/{quote(self._organization)}/{quote(self._project)}"
            "/_apis/wit/wiql?api-version=7.1"
        )
        response = request(
            self._session,
            "POST",
            url,
            timeout=self._timeout,
            json={"query": sql},
            headers={
                "Authorization": f"Basic {token}",
                "Content-Type": "application/json",
            },
        )
        status = getattr(response, "status_code", 0)
        if status >= 400:
            raise ConnectorError(f"Azure DevOps request failed with HTTP {status}.")
        try:
            payload = response.json()
        except Exception as exc:
            raise ConnectorError("Azure DevOps returned a response that is not JSON.") from exc
        work_items = payload.get("workItems") if isinstance(payload, dict) else None
        if not isinstance(work_items, list):
            raise ConnectorError("Azure DevOps returned an unexpected payload.")
        rows = [
            {"id": item.get("id"), "url": item.get("url")}
            for item in work_items
            if isinstance(item, dict)
        ]
        return pd.DataFrame(rows, columns=["id", "url"])

    def identity(self) -> dict[str, str]:
        token = base64.b64encode(f":{self._pat}".encode()).decode("ascii")
        url = (
            f"https://dev.azure.com/{quote(self._organization)}/_apis/projects/"
            f"{quote(self._project)}?api-version=7.1"
        )
        response = request(
            self._session,
            "GET",
            url,
            timeout=self._timeout,
            headers={"Authorization": f"Basic {token}"},
        )
        status = getattr(response, "status_code", 0)
        if status >= 400:
            raise ConnectorError(f"Azure DevOps identity check failed with HTTP {status}.")
        return {
            "engine": "azure_devops",
            "organization": self._organization,
            "project": self._project,
        }

    def healthcheck(self) -> bool:
        frame = self._wiql(
            "SELECT [System.Id] FROM WorkItems WHERE [System.TeamProject] = @project"
        )
        return frame is not None

    def close(self) -> None:
        close = getattr(self._session, "close", None)
        if close is not None:
            close()


def _guard_blob_path(path: str) -> None:
    if not path or any(character.isspace() for character in path):
        raise ConnectorError(
            "Azure Blob has no SQL endpoint. Pass the blob path as the query text."
        )
    parts = path.replace("\\", "/").split("/")
    if any(part == ".." for part in parts):
        raise ConnectorError("Refusing a blob path that leaves the container.")


def _guard_content_length(response: object, max_bytes: int) -> None:
    headers = getattr(response, "headers", None)
    if not isinstance(headers, Mapping):
        return
    length = headers.get("Content-Length")
    if length is None or not str(length).isdigit():
        return
    if int(length) > max_bytes:
        raise ConnectorError("Azure Blob object is larger than the cost ceiling.")
