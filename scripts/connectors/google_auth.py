"""Access tokens for Google APIs.

A bearer token in the environment is used as-is. Otherwise a service-account
file from ``GOOGLE_APPLICATION_CREDENTIALS`` is exchanged over TLS.
"""

from __future__ import annotations

import os

from connectors.base import ConnectorError

SCOPES = (
    "https://www.googleapis.com/auth/bigquery",
    "https://www.googleapis.com/auth/analytics.readonly",
)


def access_token(*env_names: str) -> str:
    for name in env_names:
        direct = os.environ.get(name, "").strip()
        if direct:
            return direct
    path = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS", "").strip()
    if not path:
        names = ", ".join(env_names) if env_names else "GOOGLE_APPLICATION_CREDENTIALS"
        raise ConnectorError(f"Set {names} or GOOGLE_APPLICATION_CREDENTIALS. See .env.example.")
    try:
        from google.auth.transport.requests import Request
        from google.oauth2 import service_account
    except ImportError as exc:
        raise ConnectorError("google-auth is required for service-account credentials.") from exc
    credentials = service_account.Credentials.from_service_account_file(path, scopes=SCOPES)
    credentials.refresh(Request())
    token = credentials.token
    if not token:
        raise ConnectorError("Google credentials did not yield an access token.")
    return str(token)
