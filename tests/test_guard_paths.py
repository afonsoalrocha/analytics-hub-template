import importlib.util
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
HOOK = ROOT / ".claude" / "hooks" / "guard_paths.py"


def _guard():
    spec = importlib.util.spec_from_file_location("guard_paths", HOOK)
    module = importlib.util.module_from_spec(spec)
    assert spec is not None and spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_hook_blocks_dotenv_and_temp_paths():
    guard = _guard()
    allowed, _ = guard.evaluate("Read", {"file_path": "README.md"})
    assert allowed
    allowed, message = guard.evaluate("Read", {"file_path": ".env"})
    assert not allowed
    assert ".env" in message
    allowed, _ = guard.evaluate("Read", {"file_path": ".env.example"})
    assert allowed
    for path in ("/tmp/extract.csv", "tmp/extract.csv", "var/temp/notes.md", "outputs/partial.tmp"):
        allowed, message = guard.evaluate("Write", {"file_path": path})
        assert not allowed, path
        assert "Temp" in message


def test_hook_forces_the_project_venv():
    guard = _guard()
    blocked = [
        "python scripts/run_demand.py",
        "python3 -m pytest",
        "venv/bin/python scripts/run_demand.py",
        "pip install -r requirements.txt",
        "cat .env",
        "source .env",
    ]
    for command in blocked:
        allowed, _ = guard.evaluate("Bash", {"command": command})
        assert not allowed, command
    allowed = [
        ".venv/bin/python scripts/run_demand.py",
        "/workspace/.venv/bin/pytest",
        "python3 -m venv .venv",
        "python3 -m venv .venv && .venv/bin/pip install -r requirements.txt",
        "make demo",
        "cat .env.example",
    ]
    for command in allowed:
        ok, message = guard.evaluate("Bash", {"command": command})
        assert ok, message


def test_hook_cli_exits_2_on_a_block_and_0_on_empty_input():
    blocked = subprocess.run(
        [sys.executable, str(HOOK)],
        input=json.dumps({"tool_name": "Read", "tool_input": {"file_path": ".env"}}),
        text=True,
        capture_output=True,
        check=False,
    )
    assert blocked.returncode == 2
    assert ".env" in blocked.stderr
    empty = subprocess.run(
        [sys.executable, str(HOOK)],
        input="",
        text=True,
        capture_output=True,
        check=False,
    )
    assert empty.returncode == 0
