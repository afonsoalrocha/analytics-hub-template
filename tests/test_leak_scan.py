import os
import subprocess
from pathlib import Path

from gates.leak_scan import (
    find_hits,
    forbidden_tracked,
    parse_denylist,
    scan,
)

ROOT = Path(__file__).resolve().parents[1]


def test_parser_skips_comments_blanks_and_short_terms():
    text = "# comment\n\nab\nreal-term\n"
    assert parse_denylist(text) == ["real-term"]


def test_matcher_is_case_insensitive_and_does_not_echo_the_line():
    hits = find_hits({"notes.md": "See SECRET_TERM_XYZ in the warehouse."}, ["secret_term_xyz"])
    assert hits == [("notes.md", "secret_term_xyz")]


def test_denylist_file_is_gitignored_and_untracked():
    tracked = subprocess.check_output(["git", "ls-files"], cwd=ROOT, text=True)
    assert ".leak-denylist.txt" not in tracked.splitlines()
    assert ".env" not in {Path(line).name for line in tracked.splitlines()}
    ignored = subprocess.check_output(
        ["git", "check-ignore", ".leak-denylist.txt"],
        cwd=ROOT,
        text=True,
    )
    assert ignored.strip() == ".leak-denylist.txt"
    assert forbidden_tracked([".leak-denylist.txt", "README.md"]) == [".leak-denylist.txt"]


def test_example_terms_do_not_appear_anywhere_else():
    example = (ROOT / ".leak-denylist.example.txt").read_text(encoding="utf-8")
    terms = parse_denylist(example)
    assert terms
    skipped = {".git", ".venv", "data", "__pycache__", ".pytest_cache", ".ruff_cache", "target"}
    contents = {}
    for directory, dirnames, filenames in os.walk(ROOT):
        dirnames[:] = [name for name in dirnames if name not in skipped]
        for filename in filenames:
            path = Path(directory) / filename
            if path.name == ".leak-denylist.example.txt":
                continue
            if path.suffix.lower() in {".png", ".duckdb", ".parquet"}:
                continue
            contents[str(path.relative_to(ROOT))] = path.read_text(
                encoding="utf-8", errors="replace"
            )
    assert find_hits(contents, terms) == []


def test_live_scan_passes_without_a_personal_denylist(tmp_path, monkeypatch):
    monkeypatch.chdir(ROOT)
    personal = ROOT / ".leak-denylist.txt"
    if personal.exists():
        personal.unlink()
    assert scan(ROOT) == []
