import json
import subprocess
from pathlib import Path

import pytest
import yaml

from mcp_wrapper import audit_config, plan
from paths import ROOT
from registry import validate_registry
from render_skills import drift
from request_worktree import close_commands, open_commands
from validate_completion import INSIGHT_HEADINGS, README_HEADINGS, assess
from validate_structure import ZERO_LLM, validate_structure

HEAVY = (
    "data/warehouse.duckdb",
    "requests/001-monthly-conversion-and-revenue/outputs/monthly_commerce.csv",
    "automations/monthly-close/snapshots/monthly_commerce.csv",
    "dbt/target/manifest.json",
    "logs/run.log",
    "extract.parquet",
    "book.xlsx",
)


def test_worktree_close_uses_a_merge_commit():
    opened = open_commands("001", "monthly-conversion-and-revenue")
    closed = close_commands("001", "monthly-conversion-and-revenue")
    assert opened == [
        "git worktree add ../worktree-request-001-monthly-conversion-and-revenue "
        "-b worktree-request-001-monthly-conversion-and-revenue main"
    ]
    assert "git merge --no-ff worktree-request-001-monthly-conversion-and-revenue" in closed
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
    architecture = ROOT / "automations" / "monthly-close" / "docs" / "ARCHITECTURE.md"
    template = ROOT / "templates" / "ARCHITECTURE.md"
    assert "## Invariants" in architecture.read_text(encoding="utf-8")
    assert ZERO_LLM in architecture.read_text(encoding="utf-8")
    assert ZERO_LLM in template.read_text(encoding="utf-8")
    for path in (ROOT / "automations").rglob("*.py"):
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
    assert assess(root, "001", closing=True).label == "complete"
    _report(root, [{"state": "warn"}])
    assert assess(root, "001", closing=True).label == "partial"
    _report(root, [{"state": "block"}])
    assert assess(root, "001", closing=True).label == "blocked"


def test_completion_blocks_a_close_without_interpretation(tmp_path):
    root = _workspace(tmp_path, insights=False, status="open")
    assert assess(root, "001", closing=False).label == "partial"
    assert assess(root, "001", closing=True).label == "blocked"
    closed = _workspace(tmp_path / "closed", insights=False, status="closed")
    assert assess(closed, "001", closing=False).label == "blocked"


def test_paused_request_cannot_carry_an_outcome(tmp_path):
    paused = _workspace(tmp_path / "paused", insights=True, status="paused")
    closing = assess(paused, "001", closing=True)
    assert closing.label == "blocked"
    assert any("outcome" in note for note in closing.notes)
    assert assess(paused, "001", closing=False).label == "complete"

    with_outcome = _workspace(
        tmp_path / "with-outcome",
        insights=True,
        status="paused",
        outcome="complete",
    )
    problems = validate_registry(with_outcome)
    assert any("paused" in problem and "outcome" in problem for problem in problems)

    open_outcome = _workspace(
        tmp_path / "open-outcome",
        insights=True,
        status="open",
        outcome="partial",
    )
    problems = validate_registry(open_outcome)
    assert any("only a closed request" in problem for problem in problems)

    mixed = _workspace(tmp_path / "mixed", insights=True, status="complete")
    problems = validate_registry(mixed)
    assert any("closing outcome" in problem for problem in problems)

    closed = _workspace(
        tmp_path / "closed-outcome",
        insights=True,
        status="closed",
        outcome="complete",
    )
    assert validate_registry(closed) == []

    lifecycle_outcome = _workspace(
        tmp_path / "lifecycle-outcome",
        insights=True,
        status="closed",
        outcome="paused",
    )
    problems = validate_registry(lifecycle_outcome)
    assert any("lifecycle status" in problem for problem in problems)


def test_completion_blocks_a_missing_heading(tmp_path):
    root = _workspace(tmp_path, insights=True, drop_heading=True)
    result = assess(root, "001", closing=True)
    assert result.label == "blocked"
    assert any("Grain" in note for note in result.notes)


def _workspace(
    root: Path,
    *,
    insights: bool,
    status: str = "closed",
    drop_heading: bool = False,
    outcome: str | None = None,
) -> Path:
    folder = root / "requests" / "001-example"
    folder.mkdir(parents=True)
    headings = [f"## {heading}" for heading in README_HEADINGS]
    if drop_heading:
        headings = [line for line in headings if line != "## Grain"]
    (folder / "README.md").write_text("\n".join(headings) + "\n", encoding="utf-8")
    (folder / "config.yaml").write_text(
        'request_id: "001"\noutputs:\n  gate_report: outputs/gate_report.json\n',
        encoding="utf-8",
    )
    if insights:
        body = "\n".join(f"## {heading}" for heading in INSIGHT_HEADINGS)
        body += "\n\n### 2026-11-10 — first reading\n\nThe number stands.\n"
        (folder / "insights.md").write_text(body, encoding="utf-8")
    entry: dict[str, object] = {
        "id": "001",
        "slug": "example",
        "path": "requests/001-example",
        "status": status,
        "transitions": [{"on": "2026-11-10", "to": status, "reason": "because"}],
    }
    if outcome is not None:
        entry["outcome"] = outcome
    registry = root / "requests" / "registry.yaml"
    registry.write_text(
        yaml.safe_dump(
            {"version": 1, "requests": [entry]},
            sort_keys=False,
        ),
        encoding="utf-8",
    )
    return root


def _report(root: Path, results: list[dict[str, str]]) -> None:
    path = root / "requests" / "001-example" / "outputs"
    path.mkdir(parents=True, exist_ok=True)
    (path / "gate_report.json").write_text(
        json.dumps({"results": results}),
        encoding="utf-8",
    )
