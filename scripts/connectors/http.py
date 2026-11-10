"""HTTPS sessions for the remote connectors.

TLS verification stays on. HTTP endpoints are refused. Retries cover
transient status codes with an explicit timeout on every call.
"""

from __future__ import annotations

from urllib.parse import urlparse

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from connectors.base import ConnectorError


def make_session(retries: int = 3, backoff: float = 0.5) -> requests.Session:
    session = requests.Session()
    retry = Retry(
        total=retries,
        connect=retries,
        read=retries,
        backoff_factor=backoff,
        status_forcelist=(429, 500, 502, 503, 504),
        allowed_methods=frozenset({"GET", "POST", "HEAD"}),
        raise_on_status=False,
    )
    session.mount("https://", HTTPAdapter(max_retries=retry))
    session.verify = True
    return session


def require_https(url: str) -> str:
    parsed = urlparse(url.strip())
    if parsed.scheme != "https" or not parsed.netloc:
        raise ConnectorError("Refusing a non-HTTPS endpoint.")
    if parsed.username or parsed.password:
        raise ConnectorError("Put credentials in environment variables, not in the URL.")
    return url.strip()


def request(
    session: requests.Session,
    method: str,
    url: str,
    *,
    timeout: float,
    **kwargs: object,
) -> requests.Response:
    safe_url = require_https(url)
    response = session.request(method, safe_url, timeout=timeout, verify=True, **kwargs)
    return response
