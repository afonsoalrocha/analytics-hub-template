"""Generic connectors. Import the class you need; nothing connects at import time."""

from connectors.azure import AzureBlobConnector, AzureDevOpsConnector
from connectors.base import Connector, ConnectorError
from connectors.bigquery import BigQueryConnector
from connectors.databricks import DatabricksConnector
from connectors.duckdb import DuckDBConnector
from connectors.ga4 import GA4Connector
from connectors.postgres import PostgresConnector

__all__ = [
    "AzureBlobConnector",
    "AzureDevOpsConnector",
    "BigQueryConnector",
    "Connector",
    "ConnectorError",
    "DatabricksConnector",
    "DuckDBConnector",
    "GA4Connector",
    "PostgresConnector",
]
