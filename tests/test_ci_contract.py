from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_github_actions_runs_lint_tests_dbt_and_the_leak_gate():
    workflow = (ROOT / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8")
    for snippet in (
        "ruff check",
        "pytest",
        "dbt build",
        "gitleaks",
        "leak_scan.py",
        "render_skills.py --check",
        "validate_structure.py",
    ):
        assert snippet in workflow
    pre_commit = (ROOT / ".pre-commit-config.yaml").read_text(encoding="utf-8")
    assert "gitleaks" in pre_commit
    assert "leak_scan.py" in pre_commit
    assert ".leak-denylist.txt" in (ROOT / ".gitignore").read_text(encoding="utf-8")
