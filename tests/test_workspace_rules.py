import json
import subprocess
from pathlib import Path

import pytest
import yaml

from demand_worktree import close_commands, open_commands
from mcp_wrapper import audit_config, plan
from paths import ROOT
from render_skills import drift
from validate_completion import INSIGHT_HEADINGS, README_HEADINGS, assess
from validate_structure import ZERO_LLM, validate_structure

HEAVY = (
    "data/warehouse.duckdb",
    "demandas/001-conversao-e-receita-mensal/outputs/monthly_commerce.csv",
    "automacoes/fechamento-mensal/snapshots/monthly_commerce.csv",
    "dbt/target/manifest.json",
    "logs/run.log",
    "extract.parquet",
    "book.xlsx",
)


def test_worktree_close_uses_a_merge_commit():
    opened = open_commands("001", "conversao-e-receita-mensal")
    closed = close_commands("001", "conversao-e-receita-mensal")
    assert opened == [
        "git worktree add ../worktree-demanda-001-conversao-e-receita-mensal "
        "-b worktree-demanda-001-conversao-e-receita-mensal main"
    ]
    assert "git merge --no-ff worktree-demanda-001-conversao-e-receita-mensal" in closed
    assert closed[0] == "git checkout main"


def test_skills_catalog_matches_frontmatter():
    assert drift(ROOT) == []


def test_repository_structure_is_complete():
    assert validate_structure(ROOT) == []


def test_heavy_artifacts_stay_out_of_git_and_logic_stays_in():
    for relative in HEAVY:
        result = subprocess.run(
            ["git", "check-ignore", "-q", relative],
            cwd=ROOT,
            check=False,
        )
        assert result.returncode == 0, relative
    logic = subprocess.run(
        ["git", "check-ignore", "-q", "dbt/models/marts/mart_monthly_commerce.sql"],
        cwd=ROOT,
        check=False,
    )
    assert logic.returncode == 1


def test_automation_declares_zero_language_model_calls():
    architecture = ROOT / "automacoes" / "fechamento-mensal" / "docs" / "ARCHITECTURE.md"
    template = ROOT / "templates" / "ARCHITECTURE.md"
    assert "## Invariants" in architecture.read_text(encoding="utf-8")
    assert ZERO_LLM in architecture.read_text(encoding="utf-8")
    assert ZERO_LLM in template.read_text(encoding="utf-8")
    for path in (ROOT / "automacoes").rglob("*.py"):
        text = path.read_text(encoding="utf-8")
        assert "import openai" not in text
        assert "api.openai.com" not in text
        assert "api.anthropic.com" not in text


def test_mcp_config_has_no_token_and_the_profile_stays_outside(tmp_path):
    assert audit_config(ROOT) == []
    outside = tmp_path / "oauth-readonly.json"
    outside.write_text(
        json.dumps({"access_token": "example-token", "read_only": True}),
        encoding="utf-8",
    )
    argv, extra = plan("filesystem", {"MCP_OAUTH_PROFILE": str(outside)}, ROOT)
    assert extra["MCP_ACCESS_TOKEN"] == "example-token"
    assert "example-token" not in " ".join(argv)
    assert argv[:3] == ["npx", "-y", "@modelcontextprotocol/server-filesystem"]
    inside = ROOT / "oauth-readonly.json"
    with pytest.raises(ValueError, match="outside"):
        plan("filesystem", {"MCP_OAUTH_PROFILE": str(inside)}, ROOT)
    writable = tmp_path / "writable.json"
    writable.write_text(json.dumps({"access_token": "example-token", "read_only": False}))
    with pytest.raises(ValueError, match="read_only"):
        plan("filesystem", {"MCP_OAUTH_PROFILE": str(writable)}, ROOT)


def test_completion_labels(tmp_path):
    root = _workspace(tmp_path, insights=True)
    assert assess(root, "001", closing=True).label == "ok"
    _report(root, [{"state": "warn"}])
    assert assess(root, "001", closing=True).label == "partial"
    _report(root, [{"state": "block"}])
    assert assess(root, "001", closing=True).label == "blocked"


def test_completion_blocks_a_close_without_interpretation(tmp_path):
    root = _workspace(tmp_path, insights=False, status="aberta")
    assert assess(root, "001", closing=False).label == "partial"
    assert assess(root, "001", closing=True).label == "blocked"
    closed = _workspace(tmp_path / "closed", insights=False, status="fechada")
    assert assess(closed, "001", closing=False).label == "blocked"


def test_completion_blocks_a_missing_heading(tmp_path):
    root = _workspace(tmp_path, insights=True, drop_heading=True)
    result = assess(root, "001", closing=True)
    assert result.label == "blocked"
    assert any("Grain" in note for note in result.notes)


def _workspace(
    root: Path,
    *,
    insights: bool,
    status: str = "fechada",
    drop_heading: bool = False,
) -> Path:
    folder = root / "demandas" / "001-exemplo"
    folder.mkdir(parents=True)
    headings = [f"## {heading}" for heading in README_HEADINGS]
    if drop_heading:
        headings = [line for line in headings if line != "## Grain"]
    (folder / "README.md").write_text("\n".join(headings) + "\n", encoding="utf-8")
    (folder / "config.yaml").write_text(
        'demand_id: "001"\noutputs:\n  gate_report: outputs/gate_report.json\n',
        encoding="utf-8",
    )
    if insights:
        body = "\n".join(f"## {heading}" for heading in INSIGHT_HEADINGS)
        body += "\n\n### 2026-11-10 — first reading\n\nThe number stands.\n"
        (folder / "insights.md").write_text(body, encoding="utf-8")
    registry = root / "demandas" / "registro.yaml"
    registry.write_text(
        yaml.safe_dump(
            {
                "version": 1,
                "demands": [
                    {
                        "id": "001",
                        "slug": "exemplo",
                        "path": "demandas/001-exemplo",
                        "status": status,
                        "transitions": [{"on": "2026-11-10", "to": status, "reason": "because"}],
                    }
                ],
            },
            sort_keys=False,
        ),
        encoding="utf-8",
    )
    return root


def _report(root: Path, results: list[dict[str, str]]) -> None:
    path = root / "demandas" / "001-exemplo" / "outputs"
    path.mkdir(parents=True, exist_ok=True)
    (path / "gate_report.json").write_text(
        json.dumps({"results": results}),
        encoding="utf-8",
    )
