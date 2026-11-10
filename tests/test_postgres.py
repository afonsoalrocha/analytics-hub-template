from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from connectors.base import ConnectorError
from connectors.postgres import PostgresConnector


def _env(monkeypatch, sslmode="verify-full"):
    monkeypatch.setenv("POSTGRES_HOST", "postgres.example.invalid")
    monkeypatch.setenv("POSTGRES_PORT", "5432")
    monkeypatch.setenv("POSTGRES_DB", "analytics")
    monkeypatch.setenv("POSTGRES_USER", "reader")
    monkeypatch.setenv("POSTGRES_PASSWORD", "example-password")
    monkeypatch.setenv("POSTGRES_SSLMODE", sslmode)


def test_disable_ssl_is_refused(monkeypatch):
    _env(monkeypatch, "disable")
    with pytest.raises(ConnectorError):
        PostgresConnector()


def test_query_uses_verify_full(monkeypatch):
    _env(monkeypatch)
    cursor = MagicMock()
    cursor.description = [SimpleNamespace(name="ok")]
    cursor.fetchall.return_value = [(1,)]
    connection = MagicMock()
    connection.cursor.return_value.__enter__.return_value = cursor
    with patch("connectors.postgres.psycopg.connect", return_value=connection) as connect:
        with PostgresConnector() as connector:
            frame = connector.query("select 1 as ok")
    assert connect.call_args.kwargs["sslmode"] == "verify-full"
    assert connect.call_args.kwargs["host"] == "postgres.example.invalid"
    assert frame["ok"].iloc[0] == 1
    connection.close.assert_called_once()
