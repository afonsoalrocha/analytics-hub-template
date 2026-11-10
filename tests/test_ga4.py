import json
from unittest.mock import MagicMock

import pytest

from connectors.base import ConnectorError
from connectors.ga4 import GA4Connector


def test_json_report_verifies_tls(monkeypatch):
    monkeypatch.setenv("GA4_PROPERTY_ID", "123456")
    monkeypatch.setenv("GA4_ACCESS_TOKEN", "example-token")
    response = MagicMock()
    response.status_code = 200
    response.json.return_value = {
        "dimensionHeaders": [{"name": "date"}],
        "metricHeaders": [{"name": "sessions"}],
        "rows": [
            {
                "dimensionValues": [{"value": "20260101"}],
                "metricValues": [{"value": "10"}],
            }
        ],
    }
    session = MagicMock()
    session.request.return_value = response
    body = json.dumps({"metrics": [{"name": "sessions"}]})
    with GA4Connector(session=session) as connector:
        frame = connector.query(body)
    assert frame.loc[0, "sessions"] == "10"
    assert session.request.call_args.args[1].startswith("https://analyticsdata.googleapis.com/")
    assert session.request.call_args.kwargs["verify"] is True


def test_sql_is_refused(monkeypatch):
    monkeypatch.setenv("GA4_PROPERTY_ID", "123456")
    monkeypatch.setenv("GA4_ACCESS_TOKEN", "example-token")
    with GA4Connector(session=MagicMock()) as connector:
        with pytest.raises(ConnectorError):
            connector.query("select sessions from events")
