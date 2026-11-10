"""Common connector interface.

Every warehouse connector exposes ``query``, ``healthcheck``, and a context
manager that closes the connection. Credentials come from the environment.
Remote calls use HTTPS and verify TLS certificates.
"""

from __future__ import annotations

from abc import ABC, abstractmethod

import pandas as pd


class ConnectorError(Exception):
    """A connector could not run. Messages omit secrets."""


class Connector(ABC):
    @abstractmethod
    def query(self, sql: str, params: dict[str, object] | None = None) -> pd.DataFrame:
        """Run a query and return a dataframe.

        SQL warehouses receive SQL. The GA4 connector receives a JSON
        RunReport body. The Azure Blob connector receives a blob path.
        """

    @abstractmethod
    def healthcheck(self) -> bool:
        """Return True when the endpoint accepts a minimal read."""

    def close(self) -> None:
        return None

    def __enter__(self) -> Connector:
        return self

    def __exit__(self, exc_type: object, exc: object, traceback: object) -> bool:
        self.close()
        return False
