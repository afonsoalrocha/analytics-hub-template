"""Fail when a denylist term appears in a tracked file, or when the denylist is tracked.

The real denylist is ``.leak-denylist.txt``. It is gitignored and is never
committed. Copy ``.leak-denylist.example.txt`` and fill it locally. In GitHub
Actions, write the repository secret ``LEAK_DENYLIST`` to that path before
running this script.

With no local denylist the content scan is a no-op and the index check still
runs, so continuous integration stays green until the owner adds the secret.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DENYLIST = ROOT / ".leak-denylist.txt"
MIN_TERM_LENGTH = 4
FORBIDDEN_TRACKED = (".leak-denylist.txt", ".env")
SKIP_SUFFIXES = {
    ".png",
    ".jpg",
    ".jpeg",
    ".gif",
    ".webp",
    ".duckdb",
    ".parquet",
    ".zip",
    ".gz",
}


def parse_denylist(text: str) -> list[str]:
    terms: list[str] = []
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if len(line) < MIN_TERM_LENGTH:
            continue
        terms.append(line.casefold())
    return terms


def git_lines(args: list[str], cwd: Path = ROOT) -> list[str]:
    completed = subprocess.run(
        ["git", *args],
        cwd=cwd,
        check=True,
        capture_output=True,
        text=True,
    )
    return [line for line in completed.stdout.splitlines() if line]


def tracked_files(cwd: Path = ROOT) -> list[str]:
    return git_lines(["ls-files"], cwd)


def forbidden_tracked(paths: list[str]) -> list[str]:
    found = []
    for path in paths:
        name = Path(path).name
        if name in FORBIDDEN_TRACKED or path in FORBIDDEN_TRACKED:
            found.append(path)
    return found


def find_hits(files: dict[str, str], terms: list[str]) -> list[tuple[str, str]]:
    hits: list[tuple[str, str]] = []
    folded_terms = [term.casefold() for term in terms]
    for path, text in files.items():
        folded = text.casefold()
        for term in folded_terms:
            if term and term in folded:
                hits.append((path, term))
    return hits


def read_tracked_text(paths: list[str], cwd: Path = ROOT) -> dict[str, str]:
    contents: dict[str, str] = {}
    for relative in paths:
        path = cwd / relative
        if not path.is_file():
            continue
        if path.suffix.lower() in SKIP_SUFFIXES:
            continue
        data = path.read_bytes()
        if b"\0" in data[:1024]:
            continue
        if len(data) > 2_000_000:
            continue
        contents[relative] = data.decode("utf-8", errors="replace")
    return contents


def scan(cwd: Path = ROOT) -> list[str]:
    problems: list[str] = []
    paths = tracked_files(cwd)
    for path in forbidden_tracked(paths):
        problems.append(f"{path} is tracked. Remove it from the git index.")
    denylist = cwd / ".leak-denylist.txt"
    if not denylist.is_file():
        return problems
    terms = parse_denylist(denylist.read_text(encoding="utf-8"))
    if not terms:
        problems.append(".leak-denylist.txt has no usable terms.")
        return problems
    searchable = {
        path: text
        for path, text in read_tracked_text(paths, cwd).items()
        if Path(path).name != ".leak-denylist.txt"
    }
    for path, term in find_hits(searchable, terms):
        problems.append(f"{path} contains a denylist term ({term}).")
    return problems


def main() -> int:
    try:
        problems = scan(ROOT)
    except subprocess.CalledProcessError as exc:
        print(f"leak-scan: git failed: {exc.stderr or exc}", file=sys.stderr)
        return 1
    if problems:
        print("leak-scan: failed")
        for problem in problems:
            print(f"leak-scan: {problem}")
        return 1
    if DENYLIST.is_file():
        print("leak-scan: denylist content check passed, and the denylist is not tracked.")
    else:
        print(
            "leak-scan: no .leak-denylist.txt, so the content scan is a no-op. "
            "The denylist is not tracked. Copy .leak-denylist.example.txt locally "
            "and set the LEAK_DENYLIST secret in CI."
        )
    return 0


if __name__ == "__main__":
    sys.exit(main())
