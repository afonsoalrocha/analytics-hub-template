from unittest.mock import MagicMock

from connectors.bigquery import BigQueryConnector


def test_query_verifies_tls_and_uses_the_bearer_token(monkeypatch):
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
    with BigQueryConnector(session=session) as connector:
        frame = connector.query("select 1 as ok", {"unused": "x"})
    assert frame["ok"].iloc[0] == "1"
    url = session.request.call_args.args[1]
    assert url.startswith("https://bigquery.googleapis.com/")
    assert session.request.call_args.kwargs["verify"] is True
    assert session.request.call_args.kwargs["headers"]["Authorization"] == "Bearer example-token"
    body = session.request.call_args.kwargs["json"]
    assert body["useLegacySql"] is False
    assert body["parameterMode"] == "NAMED"
