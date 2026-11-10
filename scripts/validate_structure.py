"""Check the repository shape.

The script checks required folders and files, registry and catalog
consistency, demand documents, product assets, automation invariants, the
generated skills catalog, and a token-free ``.mcp.json``. A demand whose
completion label is ``blocked`` fails the check. ``partial`` stays green,
because a warning is part of the review and a fresh checkout has no gate
report.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

import yaml

from catalog import validate_catalog
from mcp_wrapper import audit_config
from paths import ROOT
from registry import load_registry, validate_registry
from render_metrics import check_cards
from render_skills import drift
from validate_completion import assess

REQUIRED_DIRS = (
    "demandas",
    "verificacoes-rapidas",
    "conhecimento",
    "conhecimento/metricas",
    "conhecimento/conceitos",
    "produtos",
    "automacoes",
    "dbt",
    "dbt/models",
    "scripts/connectors",
    "scripts/gates",
    "templates",
    "templates/produto",
    "tests",
    ".claude/skills",
    ".claude/hooks",
    ".github/workflows",
)
REQUIRED_FILES = (
    "CLAUDE.md",
    "README.md",
    "README.pt-BR.md",
    "LICENSE",
    "Makefile",
    "pyproject.toml",
    "requirements.txt",
    ".env.example",
    ".gitignore",
    ".mcp.json",
    ".claude/settings.json",
    ".claude/hooks/guard_paths.py",
    "demandas/registro.yaml",
    ".github/workflows/ci.yml",
    "scripts/validate_structure.py",
    "scripts/validate_completion.py",
    "scripts/render_skills.py",
    "scripts/mcp_wrapper.py",
    "scripts/demand_worktree.py",
    "templates/produto/asset.yaml",
    "templates/produto/CHANGELOG.md",
)
GITIGNORE_SNIPPETS = (
    "*.duckdb",
    "*.parquet",
    "*.xlsx",
    "logs/",
    "demandas/**/outputs/",
    "automacoes/**/snapshots/",
    "dbt/target/",
)
ASSET_FIELDS = ("id", "name", "owner_role", "status", "sources", "refresh", "sla")
ASSET_STATUS = {"certificada", "indicativa", "bloqueada"}
ZERO_LLM = "Zero language-model calls at runtime."
LLM_IMPORT = re.compile(r"(?m)^\s*(?:import|from)\s+(openai|anthropic|litellm|langchain|cohere)\b")
LLM_HOSTS = ("api.openai.com", "api.anthropic.com")
DEMAND_DIR = re.compile(r"\d{3}-.+")


def validate_structure(root: Path = ROOT) -> list[str]:
    problems: list[str] = []
    for relative in REQUIRED_DIRS:
        if not (root / relative).is_dir():
            problems.append(f"Missing directory {relative}.")
    for relative in REQUIRED_FILES:
        if not (root / relative).is_file():
            problems.append(f"Missing file {relative}.")
    problems.extend(validate_registry(root))
    problems.extend(_demand_folders(root))
    problems.extend(validate_catalog(root))
    problems.extend(check_cards(root))
    problems.extend(drift(root))
    problems.extend(_products(root))
    problems.extend(_automations(root))
    problems.extend(_quick_checks(root))
    problems.extend(audit_config(root))
    problems.extend(_gitignore(root))
    problems.extend(_settings(root))
    problems.extend(_completion(root))
    return problems


def _demand_folders(root: Path) -> list[str]:
    try:
        document = load_registry(root)
    except (OSError, yaml.YAMLError, ValueError) as exc:
        return [str(exc)]
    demands = document.get("demands")
    if not isinstance(demands, list):
        return []
    registered = {
        f"{item.get('id')}-{item.get('slug')}" for item in demands if isinstance(item, dict)
    }
    folders = {
        path.name
        for path in (root / "demandas").iterdir()
        if path.is_dir() and DEMAND_DIR.fullmatch(path.name)
    }
    problems = []
    for name in sorted(folders - registered):
        problems.append(f"Demand folder {name} is missing from registro.yaml.")
    for name in sorted(registered - folders):
        problems.append(f"Registry entry {name} has no folder.")
    return problems


def _products(root: Path) -> list[str]:
    problems: list[str] = []
    base = root / "produtos"
    if not base.is_dir():
        return problems
    for path in sorted(item for item in base.iterdir() if item.is_dir()):
        for name in ("asset.yaml", "CHANGELOG.md", "contrato.md"):
            if not (path / name).is_file():
                problems.append(f"{path.name}: missing {name}.")
        asset_path = path / "asset.yaml"
        if asset_path.is_file():
            problems.extend(_asset(path.name, asset_path))
        changelog = path / "CHANGELOG.md"
        if changelog.is_file() and "## 20" not in changelog.read_text(encoding="utf-8"):
            problems.append(f"{path.name}: CHANGELOG.md needs a dated section.")
    return problems


def _asset(folder: str, path: Path) -> list[str]:
    try:
        document = yaml.safe_load(path.read_text(encoding="utf-8"))
    except yaml.YAMLError as exc:
        return [f"{folder}: asset.yaml is not valid YAML ({exc})."]
    if not isinstance(document, dict):
        return [f"{folder}: asset.yaml must be a mapping."]
    problems = []
    for field in ASSET_FIELDS:
        if field not in document:
            problems.append(f"{folder}: asset.yaml missing {field}.")
    if str(document.get("id")) != folder:
        problems.append(f"{folder}: asset id must match the directory name.")
    if document.get("status") not in ASSET_STATUS:
        problems.append(f"{folder}: asset status must be certificada, indicativa, or bloqueada.")
    sources = document.get("sources")
    sources_ok = isinstance(sources, list) and bool(sources)
    sources_ok = sources_ok and all(isinstance(item, str) and item for item in sources or [])
    if not sources_ok:
        problems.append(f"{folder}: asset sources must be a non-empty list of strings.")
    for field in ("owner_role", "refresh", "sla", "name"):
        if not str(document.get(field) or "").strip():
            problems.append(f"{folder}: asset {field} must be text.")
    return problems


def _automations(root: Path) -> list[str]:
    problems: list[str] = []
    base = root / "automacoes"
    if not base.is_dir():
        return problems
    for path in sorted(item for item in base.iterdir() if item.is_dir()):
        architecture = path / "docs" / "ARCHITECTURE.md"
        if not architecture.is_file():
            problems.append(f"{path.name}: missing docs/ARCHITECTURE.md.")
        else:
            text = architecture.read_text(encoding="utf-8")
            if "## Invariants" not in text:
                problems.append(f"{path.name}: ARCHITECTURE.md needs an Invariants section.")
            if ZERO_LLM not in text:
                problems.append(f"{path.name}: ARCHITECTURE.md needs the zero language-model rule.")
        for name in ("config.yaml", "run.py"):
            if not (path / name).is_file():
                problems.append(f"{path.name}: missing {name}.")
        for source in path.rglob("*.py"):
            code = source.read_text(encoding="utf-8")
            if LLM_IMPORT.search(code):
                problems.append(f"{source.relative_to(root)} imports a language-model client.")
            for host in LLM_HOSTS:
                if host in code:
                    problems.append(f"{source.relative_to(root)} calls {host}.")
    return problems


def _quick_checks(root: Path) -> list[str]:
    problems = []
    base = root / "verificacoes-rapidas"
    if not base.is_dir():
        return problems
    for path in sorted(item for item in base.iterdir() if item.is_dir()):
        for name in ("notas.md", "check.py"):
            if not (path / name).is_file():
                problems.append(f"{path.name}: missing {name}.")
    return problems


def _gitignore(root: Path) -> list[str]:
    path = root / ".gitignore"
    if not path.is_file():
        return []
    text = path.read_text(encoding="utf-8")
    return [
        f".gitignore is missing {snippet}." for snippet in GITIGNORE_SNIPPETS if snippet not in text
    ]


def _settings(root: Path) -> list[str]:
    path = root / ".claude" / "settings.json"
    if not path.is_file():
        return []
    text = path.read_text(encoding="utf-8")
    if "guard_paths.py" not in text:
        return [".claude/settings.json must run guard_paths.py."]
    return []


def _completion(root: Path) -> list[str]:
    try:
        document = load_registry(root)
    except (OSError, yaml.YAMLError, ValueError):
        return []
    demands = document.get("demands")
    if not isinstance(demands, list):
        return []
    problems = []
    for item in demands:
        if not isinstance(item, dict):
            continue
        demand_id = str(item.get("id"))
        result = assess(root, demand_id, closing=False)
        if result.label == "blocked":
            detail = "; ".join(result.notes)
            problems.append(f"{demand_id}: completion is blocked ({detail}).")
    return problems


def main() -> int:
    problems = validate_structure(ROOT)
    if problems:
        for problem in problems:
            print(f"structure: {problem}")
        return 1
    print("structure: repository shape matches the template.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
