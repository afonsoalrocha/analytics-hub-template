"""Read-only, dry-run, and cost-ceiling rules shared by every connector.

A connector accepts one read statement unless ``CONNECTOR_ALLOW_WRITE`` is
true. ``CONNECTOR_DRY_RUN`` returns the statement and the byte ceiling and
makes no network call. ``CONNECTOR_MAX_BYTES`` is that ceiling. BigQuery
sends it as ``maximumBytesBilled``. Databricks sends it as ``byte_limit``,
which caps the bytes the Statement API returns.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

import pandas as pd

from connectors.base import ConnectorError
from connectors.env import env_bool, env_int

DEFAULT_MAX_BYTES = 1_073_741_824
READ_HEADS = frozenset({"select", "with", "show", "describe", "desc", "explain", "values"})
WRITE_WORDS = frozenset(
    {
        "insert",
        "update",
        "delete",
        "drop",
        "alter",
        "create",
        "merge",
        "truncate",
        "grant",
        "revoke",
    }
)


@dataclass(frozen=True)
class Policy:
    dry_run: bool
    allow_write: bool
    max_bytes: int


def load_policy(
    *,
    dry_run: bool | None = None,
    allow_write: bool | None = None,
    max_bytes: int | None = None,
) -> Policy:
    return Policy(
        dry_run=env_bool("CONNECTOR_DRY_RUN", False) if dry_run is None else dry_run,
        allow_write=(
            env_bool("CONNECTOR_ALLOW_WRITE", False) if allow_write is None else allow_write
        ),
        max_bytes=env_int("CONNECTOR_MAX_BYTES", DEFAULT_MAX_BYTES)
        if max_bytes is None
        else max_bytes,
    )


def ensure_ceiling(policy: Policy) -> None:
    if policy.max_bytes <= 0:
        raise ConnectorError("Cost ceiling must be a positive number of bytes.")


def apply_sql(policy: Policy, sql: str, *, engine: str) -> pd.DataFrame | None:
    """Return a dry-run frame, or None when the caller should execute ``sql``."""

    ensure_ceiling(policy)
    if not policy.allow_write and not is_read_only_sql(sql):
        raise ConnectorError(
            "Connector is read-only. Set CONNECTOR_ALLOW_WRITE=true to run a write."
        )
    if policy.dry_run:
        return dry_run_frame(sql, engine=engine, max_bytes=policy.max_bytes)
    return None


def dry_run_frame(statement: str, *, engine: str, max_bytes: int) -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "engine": engine,
                "dry_run": True,
                "statement": statement,
                "max_bytes": max_bytes,
            }
        ]
    )


def is_read_only_sql(sql: str) -> bool:
    body = _statement_body(sql)
    if not body or ";" in body:
        return False
    match = re.match(r"[A-Za-z_]+", body)
    if match is None or match.group(0).lower() not in READ_HEADS:
        return False
    words = {word.lower() for word in re.findall(r"[A-Za-z_]+", body)}
    return WRITE_WORDS.isdisjoint(words)


def _statement_body(sql: str) -> str:
    cleaned = _strip_literals(sql).strip()
    while cleaned.startswith("("):
        cleaned = cleaned[1:].strip()
    if cleaned.endswith(";"):
        cleaned = cleaned[:-1].strip()
    return cleaned


def _strip_literals(sql: str) -> str:
    pieces: list[str] = []
    index = 0
    length = len(sql)
    while index < length:
        if sql.startswith("--", index):
            newline = sql.find("\n", index)
            if newline < 0:
                break
            index = newline
            continue
        if sql.startswith("/*", index):
            end = sql.find("*/", index + 2)
            if end < 0:
                break
            index = end + 2
            continue
        if sql[index] in {"'", '"'}:
            quote = sql[index]
            index += 1
            while index < length:
                if sql[index] == quote:
                    if index + 1 < length and sql[index + 1] == quote:
                        index += 2
                        continue
                    index += 1
                    break
                index += 1
            pieces.append(" ")
            continue
        pieces.append(sql[index])
        index += 1
    return "".join(pieces)
