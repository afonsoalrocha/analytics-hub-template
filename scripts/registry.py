"""Validate the request registry, the single index of requests."""

from __future__ import annotations

from datetime import date
from pathlib import Path

import yaml

from paths import ROOT

STATUSES = {"open", "in_spec", "in_build", "in_interpretation", "closed", "paused"}
OUTCOMES = {"complete", "partial", "blocked"}


def load_registry(root: Path = ROOT) -> dict[str, object]:
    document = yaml.safe_load((root / "requests" / "registry.yaml").read_text(encoding="utf-8"))
    if not isinstance(document, dict):
        raise ValueError("requests/registry.yaml must be a mapping.")
    normalized = _normalize_yaml(document)
    if not isinstance(normalized, dict):
        raise ValueError("requests/registry.yaml must be a mapping.")
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
    requests = document.get("requests")
    if not isinstance(requests, list) or not requests:
        return ["registry.yaml needs a non-empty requests list."]
    problems: list[str] = []
    seen: set[str] = set()
    for request in requests:
        if not isinstance(request, dict):
            problems.append("Each request must be a mapping.")
            continue
        request_id = str(request.get("id"))
        slug = str(request.get("slug"))
        if request_id in seen:
            problems.append(f"Duplicate request id {request_id}.")
        seen.add(request_id)
        folder = root / "requests" / f"{request_id}-{slug}"
        declared = root / str(request.get("path"))
        if declared != folder:
            problems.append(f"{request_id}: path must be requests/{request_id}-{slug}.")
        if not folder.is_dir():
            problems.append(f"{request_id}: folder {folder.name} is missing.")
            continue
        if not (folder / "README.md").is_file():
            problems.append(f"{request_id}: README.md is missing.")
        transitions = request.get("transitions")
        if not isinstance(transitions, list) or not transitions:
            problems.append(f"{request_id}: transitions are required.")
            continue
        previous: date | None = None
        last_status = None
        for transition in transitions:
            if not isinstance(transition, dict):
                problems.append(f"{request_id}: a transition is not a mapping.")
                continue
            status = transition.get("to")
            problem = _lifecycle_problem(request_id, status, where=f"transition to {status}")
            if problem:
                problems.append(problem)
            try:
                current = date.fromisoformat(str(transition.get("on")))
            except ValueError:
                problems.append(f"{request_id}: transition date must be YYYY-MM-DD.")
                continue
            if previous is not None and current < previous:
                problems.append(f"{request_id}: transitions must stay in date order.")
            if not str(transition.get("reason") or "").strip():
                problems.append(f"{request_id}: every transition needs a reason.")
            previous = current
            last_status = status
        status = request.get("status")
        problem = _lifecycle_problem(request_id, status, where=f"status {status}")
        if problem:
            problems.append(problem)
        elif status != last_status:
            problems.append(f"{request_id}: status must equal the latest transition.")
        problems.extend(_outcome_problems(request_id, request))
        if status == "closed" and not (folder / "insights.md").is_file():
            problems.append(f"{request_id}: a closed request needs insights.md.")
    return problems


def _lifecycle_problem(request_id: str, status: object, *, where: str) -> str | None:
    if status in OUTCOMES:
        return f"{request_id}: {where} is a closing outcome, not a lifecycle status."
    if status not in STATUSES:
        return f"{request_id}: unknown status {status}."
    return None


def _outcome_problems(request_id: str, request: dict[str, object]) -> list[str]:
    if "outcome" not in request or request.get("outcome") is None:
        return []
    outcome = request.get("outcome")
    status = request.get("status")
    problems: list[str] = []
    if status == "paused":
        problems.append(f"{request_id}: a paused request cannot carry an outcome.")
    elif status != "closed":
        problems.append(f"{request_id}: only a closed request can carry an outcome.")
    if outcome in STATUSES:
        problems.append(f"{request_id}: outcome must not be a lifecycle status ({outcome}).")
    elif outcome not in OUTCOMES:
        problems.append(f"{request_id}: outcome must be complete, partial, or blocked.")
    return problems
