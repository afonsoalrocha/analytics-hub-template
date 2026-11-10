from unittest.mock import MagicMock

import pytest

from connectors.base import ConnectorError
from connectors.databricks import DatabricksConnector


def _env(monkeypatch, host="https://workspace.example.invalid"):
    monkeypatch.setenv("DATABRICKS_HOST", host)
    monkeypatch.setenv("DATABRICKS_TOKEN", "example-token")
    monkeypatch.setenv("DATABRICKS_WAREHOUSE_ID", "warehouse-example")


def _succeeded():
    response = MagicMock()
    response.status_code = 200
    response.json.return_value = {
        "statement_id": "stmt-1",
        "status": {"state": "SUCCEEDED"},
        "manifest": {"schema": {"columns": [{"name": "ok"}]}},
        "result": {"data_array": [[1]]},
    }
    return response


def test_query_verifies_tls(monkeypatch):
    _env(monkeypatch)
    session = MagicMock()
    session.request.return_value = _succeeded()
    with DatabricksConnector(session=session) as connector:
        frame = connector.query("select 1 as ok")
    assert frame["ok"].iloc[0] == 1
    method, url = session.request.call_args.args
    assert method == "POST"
    assert url.startswith("https://workspace.example.invalid/")
    assert session.request.call_args.kwargs["verify"] is True


def test_http_host_is_refused(monkeypatch):
    _env(monkeypatch, "http://workspace.example.invalid")
    with pytest.raises(ConnectorError):
        DatabricksConnector(session=MagicMock())


def test_pending_statement_is_polled(monkeypatch):
    _env(monkeypatch)
    pending = MagicMock()
    pending.status_code = 200
    pending.json.return_value = {
        "statement_id": "stmt-2",
        "status": {"state": "RUNNING"},
    }
    session = MagicMock()
    session.request.side_effect = [pending, _succeeded()]
    with DatabricksConnector(session=session) as connector:
        frame = connector.query("select 1 as ok")
    assert frame["ok"].iloc[0] == 1
    assert session.request.call_count == 2
    assert session.request.call_args_list[1].args[0] == "GET"
