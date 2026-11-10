from io import BytesIO
from unittest.mock import MagicMock

import pytest

from connectors.azure import AzureBlobConnector, AzureDevOpsConnector
from connectors.base import ConnectorError


def test_blob_reads_csv_over_https(monkeypatch):
    monkeypatch.setenv("AZURE_STORAGE_ACCOUNT", "exampleaccount")
    monkeypatch.setenv("AZURE_STORAGE_CONTAINER", "example-container")
    monkeypatch.setenv("AZURE_STORAGE_SAS_TOKEN", "sig=example")
    response = MagicMock()
    response.status_code = 200
    response.content = b"order_id,price\nord_1,10.0\n"
    session = MagicMock()
    session.request.return_value = response
    with AzureBlobConnector(session=session) as connector:
        frame = connector.query("folder/orders.csv")
    assert frame["order_id"].iloc[0] == "ord_1"
    url = session.request.call_args.args[1]
    assert url.startswith("https://exampleaccount.blob.core.windows.net/")
    assert session.request.call_args.kwargs["verify"] is True
    assert " " not in url.split("?", 1)[0]


def test_blob_refuses_a_sql_string(monkeypatch):
    monkeypatch.setenv("AZURE_STORAGE_ACCOUNT", "exampleaccount")
    monkeypatch.setenv("AZURE_STORAGE_CONTAINER", "example-container")
    monkeypatch.setenv("AZURE_STORAGE_SAS_TOKEN", "sig=example")
    with AzureBlobConnector(session=MagicMock()) as connector:
        with pytest.raises(ConnectorError):
            connector.query("select * from orders")


def test_devops_posts_wiql_over_https(monkeypatch):
    monkeypatch.setenv("AZURE_DEVOPS_ORG", "example-org")
    monkeypatch.setenv("AZURE_DEVOPS_PROJECT", "example-project")
    monkeypatch.setenv("AZURE_DEVOPS_PAT", "example-pat")
    response = MagicMock()
    response.status_code = 200
    response.json.return_value = {"workItems": [{"id": 7, "url": "https://dev.azure.com/item/7"}]}
    session = MagicMock()
    session.request.return_value = response
    statement = "SELECT [System.Id] FROM WorkItems"
    with AzureDevOpsConnector(session=session) as connector:
        frame = connector.query(statement)
    assert frame["id"].iloc[0] == 7
    url = session.request.call_args.args[1]
    assert url.startswith("https://dev.azure.com/example-org/example-project/")
    assert session.request.call_args.kwargs["verify"] is True
    assert session.request.call_args.kwargs["json"] == {"query": statement}


def test_blob_payload_is_parsed_without_network(monkeypatch):
    monkeypatch.setenv("AZURE_STORAGE_ACCOUNT", "exampleaccount")
    monkeypatch.setenv("AZURE_STORAGE_CONTAINER", "example-container")
    monkeypatch.setenv("AZURE_STORAGE_SAS_TOKEN", "?sig=example")
    response = MagicMock()
    response.status_code = 200
    response.content = BytesIO(b"n\n1\n").getvalue()
    session = MagicMock()
    session.request.return_value = response
    with AzureBlobConnector(session=session) as connector:
        frame = connector.query("n.csv")
    assert int(frame["n"].iloc[0]) == 1
