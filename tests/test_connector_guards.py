from unittest.mock import MagicMock

import pytest

from connectors.azure import AzureBlobConnector, AzureDevOpsConnector
from connectors.base import ConnectorError
from connectors.bigquery import BigQueryConnector
from connectors.databricks import DatabricksConnector
from connectors.duckdb import DuckDBConnector
from connectors.ga4 import GA4Connector
from connectors.policy import Policy
from connectors.postgres import PostgresConnector

READ = Policy(dry_run=False, allow_write=False, max_bytes=1024)
DRY = Policy(dry_run=True, allow_write=False, max_bytes=1024)


def test_duckdb_blocks_writes_and_previews_a_dry_run(tmp_path):
    with DuckDBConnector(str(tmp_path / "local.duckdb"), policy=READ) as connector:
        with pytest.raises(ConnectorError):
            connector.query("delete from orders")
        identity = connector.identity()
    assert identity["engine"] == "duckdb"
    assert identity["database"].endswith("local.duckdb")
    with DuckDBConnector(str(tmp_path / "local.duckdb"), policy=DRY) as connector:
        frame = connector.query("select 1 as ok")
    assert bool(frame["dry_run"].iloc[0]) is True
    assert int(frame["max_bytes"].iloc[0]) == 1024


def test_postgres_blocks_a_write_before_execute(monkeypatch):
    monkeypatch.setenv("POSTGRES_HOST", "postgres.example.invalid")
    monkeypatch.setenv("POSTGRES_DB", "analytics")
    monkeypatch.setenv("POSTGRES_USER", "reader")
    monkeypatch.setenv("POSTGRES_PASSWORD", "example-password")
    cursor = MagicMock()
    cursor.description = [
        type("Column", (), {"name": "user_name"})(),
        type("Column", (), {"name": "database_name"})(),
    ]
    cursor.fetchall.return_value = [("reader", "analytics")]
    connection = MagicMock()
    connection.cursor.return_value.__enter__.return_value = cursor
    monkeypatch.setattr("connectors.postgres.psycopg.connect", lambda **kwargs: connection)
    with PostgresConnector(policy=READ) as connector:
        with pytest.raises(ConnectorError):
            connector.query("delete from orders")
        identity = connector.identity()
    cursor.execute.assert_called_once()
    assert identity["user_name"] == "reader"
    assert "delete" not in cursor.execute.call_args.args[0]


def test_databricks_sends_the_byte_ceiling_and_can_preview(monkeypatch):
    monkeypatch.setenv("DATABRICKS_HOST", "https://workspace.example.invalid")
    monkeypatch.setenv("DATABRICKS_TOKEN", "example-token")
    monkeypatch.setenv("DATABRICKS_WAREHOUSE_ID", "warehouse-example")
    session = MagicMock()
    response = MagicMock()
    response.status_code = 200
    response.json.return_value = {
        "status": {"state": "SUCCEEDED"},
        "manifest": {"schema": {"columns": [{"name": "ok"}]}},
        "result": {"data_array": [[1]]},
    }
    session.request.return_value = response
    with DatabricksConnector(session=session, policy=READ) as connector:
        with pytest.raises(ConnectorError):
            connector.query("delete from orders")
        connector.query("select 1 as ok")
    assert session.request.call_count == 1
    assert session.request.call_args.kwargs["json"]["byte_limit"] == 1024
    session.request.reset_mock()
    with DatabricksConnector(session=session, policy=DRY) as connector:
        frame = connector.query("select 1 as ok")
    assert bool(frame["dry_run"].iloc[0]) is True
    session.request.assert_not_called()


def test_databricks_identity_reads_the_account(monkeypatch):
    monkeypatch.setenv("DATABRICKS_HOST", "https://workspace.example.invalid")
    monkeypatch.setenv("DATABRICKS_TOKEN", "example-token")
    monkeypatch.setenv("DATABRICKS_WAREHOUSE_ID", "warehouse-example")
    response = MagicMock()
    response.status_code = 200
    response.json.return_value = {"userName": "analyst@example.invalid"}
    session = MagicMock()
    session.request.return_value = response
    with DatabricksConnector(session=session, policy=READ) as connector:
        identity = connector.identity()
    assert identity["user_name"] == "analyst@example.invalid"
    assert session.request.call_args.args[0] == "GET"
    assert session.request.call_args.args[1].endswith("/Me")


def test_bigquery_sends_maximum_bytes_billed(monkeypatch):
    monkeypatch.setenv("BIGQUERY_PROJECT", "example-project")
    monkeypatch.setenv("BIGQUERY_ACCESS_TOKEN", "example-token")
    monkeypatch.delenv("GOOGLE_APPLICATION_CREDENTIALS", raising=False)
    response = MagicMock()
    response.status_code = 200
    response.json.return_value = {
        "jobComplete": True,
        "schema": {"fields": [{"name": "ok"}]},
        "rows": [{"f": [{"v": "1"}]}],
    }
    session = MagicMock()
    session.request.return_value = response
    with BigQueryConnector(session=session, policy=READ) as connector:
        with pytest.raises(ConnectorError):
            connector.query("drop table orders")
        connector.query("select 1 as ok")
    body = session.request.call_args.kwargs["json"]
    assert body["maximumBytesBilled"] == "1024"
    session.request.reset_mock()
    with BigQueryConnector(session=session, policy=DRY) as connector:
        connector.query("select 1 as ok")
    session.request.assert_not_called()


def test_bigquery_identity_reads_the_project(monkeypatch):
    monkeypatch.setenv("BIGQUERY_PROJECT", "example-project")
    monkeypatch.setenv("BIGQUERY_ACCESS_TOKEN", "example-token")
    monkeypatch.delenv("GOOGLE_APPLICATION_CREDENTIALS", raising=False)
    response = MagicMock()
    response.status_code = 200
    response.json.return_value = {"id": "example-project"}
    session = MagicMock()
    session.request.return_value = response
    with BigQueryConnector(session=session, policy=READ) as connector:
        identity = connector.identity()
    assert identity["project"] == "example-project"
    assert session.request.call_args.args[0] == "GET"


def test_ga4_dry_run_skips_the_network_and_blocks_a_write_method(monkeypatch):
    monkeypatch.setenv("GA4_PROPERTY_ID", "123456")
    monkeypatch.setenv("GA4_ACCESS_TOKEN", "example-token")
    session = MagicMock()
    report = '{"metrics": [{"name": "sessions"}]}'
    with GA4Connector(session=session, policy=DRY) as connector:
        frame = connector.query(report)
    assert frame["engine"].iloc[0] == "ga4"
    session.request.assert_not_called()
    with GA4Connector(session=session, policy=READ) as connector:
        with pytest.raises(ConnectorError):
            connector.query('{"method": "createUser"}')


def test_ga4_identity_reads_property_metadata(monkeypatch):
    monkeypatch.setenv("GA4_PROPERTY_ID", "123456")
    monkeypatch.setenv("GA4_ACCESS_TOKEN", "example-token")
    response = MagicMock()
    response.status_code = 200
    session = MagicMock()
    session.request.return_value = response
    with GA4Connector(session=session, policy=READ) as connector:
        identity = connector.identity()
    assert identity["property_id"] == "123456"
    assert session.request.call_args.args[1].endswith("/metadata")


def test_blob_refuses_parent_paths_and_oversized_objects(monkeypatch):
    monkeypatch.setenv("AZURE_STORAGE_ACCOUNT", "exampleaccount")
    monkeypatch.setenv("AZURE_STORAGE_CONTAINER", "example-container")
    monkeypatch.setenv("AZURE_STORAGE_SAS_TOKEN", "sig=example")
    session = MagicMock()
    with AzureBlobConnector(session=session, policy=READ) as connector:
        with pytest.raises(ConnectorError):
            connector.query("../secret.csv")
    session.request.assert_not_called()
    response = MagicMock()
    response.status_code = 200
    response.headers = {"Content-Length": "5000"}
    response.content = b"n\n1\n"
    session.request.return_value = response
    with AzureBlobConnector(session=session, policy=READ) as connector:
        with pytest.raises(ConnectorError):
            connector.query("orders.csv")
        identity = connector.identity()
    assert identity["account"] == "exampleaccount"
    assert "sig" not in identity.values()


def test_devops_blocks_a_write_and_reads_the_project(monkeypatch):
    monkeypatch.setenv("AZURE_DEVOPS_ORG", "example-org")
    monkeypatch.setenv("AZURE_DEVOPS_PROJECT", "example-project")
    monkeypatch.setenv("AZURE_DEVOPS_PAT", "example-pat")
    response = MagicMock()
    response.status_code = 200
    response.json.return_value = {"name": "example-project"}
    session = MagicMock()
    session.request.return_value = response
    with AzureDevOpsConnector(session=session, policy=READ) as connector:
        with pytest.raises(ConnectorError):
            connector.query("DELETE FROM WorkItems")
        identity = connector.identity()
    assert identity["organization"] == "example-org"
    assert session.request.call_args.args[0] == "GET"
