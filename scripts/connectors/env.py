"""Read connector settings from the environment."""

from __future__ import annotations

import os

from connectors.base import ConnectorError


def require_env(name: str) -> str:
    value = os.environ.get(name, "").strip()
    if not value:
        raise ConnectorError(f"Missing environment variable {name}. See .env.example.")
    return value


def env_int(name: str, default: int) -> int:
    raw = os.environ.get(name, "").strip()
    if not raw:
        return default
    try:
        return int(raw)
    except ValueError as exc:
        raise ConnectorError(f"{name} must be an integer.") from exc


def env_float(name: str, default: float) -> float:
    raw = os.environ.get(name, "").strip()
    if not raw:
        return default
    try:
        return float(raw)
    except ValueError as exc:
        raise ConnectorError(f"{name} must be a number.") from exc
