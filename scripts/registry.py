"""Validate the demand registry, the single index of demands."""

from __future__ import annotations

from datetime import date
from pathlib import Path

import yaml

from paths import ROOT

STATUSES = {"aberta", "em_spec", "em_build", "em_interpretacao", "fechada", "pausada"}


def load_registry(root: Path = ROOT) -> dict[str, object]:
    document = yaml.safe_load((root / "demandas" / "registro.yaml").read_text(encoding="utf-8"))
    if not isinstance(document, dict):
        raise ValueError("demandas/registro.yaml must be a mapping.")
    normalized = _normalize_yaml(document)
    if not isinstance(normalized, dict):
        raise ValueError("demandas/registro.yaml must be a mapping.")
    return normalized


def _normalize_yaml(value: object) -> object:
    if isinstance(value, date):
        return value.isoformat()
    if isinstance(value, dict):
        normalized = {}
        for key, item in value.items():
            if key is True:
                key = "on"
            elif key is False:
                key = "off"
            normalized[str(key)] = _normalize_yaml(item)
        return normalized
    if isinstance(value, list):
        return [_normalize_yaml(item) for item in value]
    return value


def validate_registry(root: Path = ROOT) -> list[str]:
    try:
        document = load_registry(root)
    except (OSError, yaml.YAMLError, ValueError) as exc:
        return [str(exc)]
    demands = document.get("demands")
    if not isinstance(demands, list) or not demands:
        return ["registro.yaml needs a non-empty demands list."]
    problems: list[str] = []
    seen: set[str] = set()
    for demand in demands:
        if not isinstance(demand, dict):
            problems.append("Each demand must be a mapping.")
            continue
        demand_id = str(demand.get("id"))
        slug = str(demand.get("slug"))
        if demand_id in seen:
            problems.append(f"Duplicate demand id {demand_id}.")
        seen.add(demand_id)
        folder = root / "demandas" / f"{demand_id}-{slug}"
        declared = root / str(demand.get("path"))
        if declared != folder:
            problems.append(f"{demand_id}: path must be demandas/{demand_id}-{slug}.")
        if not folder.is_dir():
            problems.append(f"{demand_id}: folder {folder.name} is missing.")
            continue
        if not (folder / "README.md").is_file():
            problems.append(f"{demand_id}: README.md is missing.")
        transitions = demand.get("transitions")
        if not isinstance(transitions, list) or not transitions:
            problems.append(f"{demand_id}: transitions are required.")
            continue
        previous: date | None = None
        last_status = None
        for transition in transitions:
            if not isinstance(transition, dict):
                problems.append(f"{demand_id}: a transition is not a mapping.")
                continue
            status = transition.get("to")
            if status not in STATUSES:
                problems.append(f"{demand_id}: unknown status {status}.")
            try:
                current = date.fromisoformat(str(transition.get("on")))
            except ValueError:
                problems.append(f"{demand_id}: transition date must be YYYY-MM-DD.")
                continue
            if previous is not None and current < previous:
                problems.append(f"{demand_id}: transitions must stay in date order.")
            if not str(transition.get("reason") or "").strip():
                problems.append(f"{demand_id}: every transition needs a reason.")
            previous = current
            last_status = status
        if demand.get("status") != last_status:
            problems.append(f"{demand_id}: status must equal the latest transition.")
        if demand.get("status") == "fechada" and not (folder / "insights.md").is_file():
            problems.append(f"{demand_id}: a closed demand needs insights.md.")
    return problems
