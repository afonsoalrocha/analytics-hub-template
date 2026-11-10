"""Metric catalog: one YAML card per metric, validated by schema."""

from __future__ import annotations

from datetime import date
from pathlib import Path
from typing import Any

import yaml
from jsonschema import Draft202012Validator

from paths import ROOT

STATUSES = ("certificada", "indicativa", "bloqueada")

METRIC_SCHEMA: dict[str, Any] = {
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "type": "object",
    "additionalProperties": False,
    "required": [
        "id",
        "name",
        "status",
        "definition",
        "formula",
        "grain",
        "default_date_column",
        "required_filters",
        "allowed_dimensions",
        "maturity_days",
        "reconciliation_source",
        "owner",
        "decided_at",
        "block_reason",
        "history",
    ],
    "properties": {
        "id": {"type": "string", "pattern": "^[a-z][a-z0-9_]*$"},
        "name": {"type": "string", "minLength": 3},
        "status": {"type": "string", "enum": list(STATUSES)},
        "definition": {"type": "string", "minLength": 10},
        "formula": {
            "type": "object",
            "additionalProperties": False,
            "required": ["numerator", "denominator", "aggregation"],
            "properties": {
                "numerator": {"type": "string", "minLength": 3},
                "denominator": {"type": ["string", "null"]},
                "aggregation": {"type": "string", "minLength": 3},
            },
        },
        "grain": {"type": "string", "minLength": 3},
        "default_date_column": {"type": "string", "minLength": 3},
        "required_filters": {"type": "array", "items": {"type": "string"}},
        "allowed_dimensions": {
            "type": "array",
            "items": {
                "type": "object",
                "additionalProperties": False,
                "required": ["name", "caution"],
                "properties": {
                    "name": {"type": "string", "minLength": 2},
                    "caution": {"type": "string"},
                },
            },
        },
        "maturity_days": {"type": "integer", "minimum": 0},
        "reconciliation_source": {"type": "string", "minLength": 3},
        "owner": {"type": "string", "minLength": 3},
        "decided_at": {"type": "string", "minLength": 10},
        "block_reason": {"type": ["string", "null"]},
        "history": {
            "type": "array",
            "minItems": 1,
            "items": {
                "type": "object",
                "additionalProperties": False,
                "required": ["on", "change"],
                "properties": {
                    "on": {"type": "string", "minLength": 10},
                    "change": {"type": "string", "minLength": 3},
                },
            },
        },
        "published_components": {
            "type": "array",
            "items": {"type": "string", "minLength": 2},
        },
    },
    "allOf": [
        {
            "if": {"properties": {"status": {"const": "bloqueada"}}, "required": ["status"]},
            "then": {"properties": {"block_reason": {"type": "string", "minLength": 10}}},
            "else": {"properties": {"block_reason": {"type": "null"}}},
        }
    ],
}

VALIDATOR = Draft202012Validator(METRIC_SCHEMA)


def metric_dir(root: Path = ROOT) -> Path:
    return root / "conhecimento" / "metricas"


def load_cards(root: Path = ROOT) -> list[dict[str, Any]]:
    cards = []
    for path in sorted(metric_dir(root).glob("*.yaml")):
        document = yaml.safe_load(path.read_text(encoding="utf-8"))
        if not isinstance(document, dict):
            raise ValueError(f"{path} is not a metric card.")
        cards.append(_stringify_dates(document))
    return cards


def _stringify_dates(value: Any) -> Any:
    # PyYAML 1.1 reads an unquoted date as datetime.date and an unquoted
    # key `on` as True. Both show up in hand-written cards.
    if isinstance(value, date):
        return value.isoformat()
    if isinstance(value, dict):
        normalized: dict[Any, Any] = {}
        for key, item in value.items():
            if key is True:
                key = "on"
            elif key is False:
                key = "off"
            normalized[key] = _stringify_dates(item)
        return normalized
    if isinstance(value, list):
        return [_stringify_dates(item) for item in value]
    return value


def validate_card(card: dict[str, Any], source: str) -> list[str]:
    errors = []
    for error in sorted(VALIDATOR.iter_errors(card), key=lambda item: list(item.path)):
        location = "/".join(str(part) for part in error.path) or "(card)"
        errors.append(f"{source}: {location}: {error.message}")
    if card.get("id") and source and not source.endswith(f"{card['id']}.yaml"):
        errors.append(f"{source}: file name must match id {card.get('id')}.")
    errors.extend(_date_errors(card, source))
    return errors


def _date_errors(card: dict[str, Any], source: str) -> list[str]:
    problems: list[str] = []
    if not _is_date(card.get("decided_at")):
        problems.append(f"{source}: decided_at must be YYYY-MM-DD.")
    history = card.get("history")
    if isinstance(history, list):
        for index, entry in enumerate(history):
            if isinstance(entry, dict) and not _is_date(entry.get("on")):
                problems.append(f"{source}: history/{index}/on must be YYYY-MM-DD.")
    return problems


def _is_date(value: object) -> bool:
    try:
        date.fromisoformat(str(value))
    except ValueError:
        return False
    return True


def validate_catalog(root: Path = ROOT) -> list[str]:
    problems: list[str] = []
    seen: set[str] = set()
    for path in sorted(metric_dir(root).glob("*.yaml")):
        document = yaml.safe_load(path.read_text(encoding="utf-8"))
        if not isinstance(document, dict):
            problems.append(f"{path.name}: not a mapping")
            continue
        document = _stringify_dates(document)
        problems.extend(validate_card(document, path.name))
        metric_id = str(document.get("id"))
        if metric_id in seen:
            problems.append(f"{path.name}: duplicate id {metric_id}")
        seen.add(metric_id)
    index_path = root / "conhecimento" / "index.yaml"
    index = yaml.safe_load(index_path.read_text(encoding="utf-8"))
    listed = index.get("metrics", []) if isinstance(index, dict) else []
    listed_ids = [item.get("id") for item in listed if isinstance(item, dict)]
    if sorted(listed_ids) != sorted(seen):
        problems.append("conhecimento/index.yaml metric ids must match the metric card files.")
    for item in listed:
        if not isinstance(item, dict):
            continue
        relative = item.get("path")
        if relative != f"conhecimento/metricas/{item.get('id')}.yaml":
            problems.append(f"index path for {item.get('id')} must point at its YAML card.")
        markdown = root / "conhecimento" / "metricas" / f"{item.get('id')}.md"
        if not markdown.is_file():
            problems.append(f"missing rendered card {markdown.name}")
    return problems
