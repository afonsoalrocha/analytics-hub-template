from pathlib import Path

import pytest

from connectors.base import ConnectorError
from connectors.http import make_session, require_https

ROOT = Path(__file__).resolve().parents[1]
BANNED = (
    "verify=False",
    "verify = False",
    "sslmode='disable'",
    'sslmode="disable"',
    "sslmode='allow'",
    "sslmode='prefer'",
    "CERT_NONE",
)


def test_connector_sources_keep_tls_verification_on():
    for path in (ROOT / "scripts" / "connectors").rglob("*.py"):
        text = path.read_text(encoding="utf-8")
        for token in BANNED:
            assert token not in text, f"{path.name} contains {token}"


def test_session_verifies_certificates_and_retries_on_https():
    session = make_session()
    assert session.verify is True
    assert "https://" in session.adapters


def test_plain_http_is_refused():
    with pytest.raises(ConnectorError):
        require_https("http://warehouse.example.invalid/query")


def test_credentials_in_the_url_are_refused():
    with pytest.raises(ConnectorError):
        require_https("https://user:secret@warehouse.example.invalid/query")
