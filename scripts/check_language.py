"""Fail if a tracked file uses a Portuguese token or an accented letter.

``README.pt-BR.md`` is the optional translation. ``LICENSE`` is excluded.
Every other tracked file is English. The token list is stored as code points
so this source does not contain the strings it searches for.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

from paths import ROOT

EXCLUDED_NAMES = {"README.pt-BR.md", "LICENSE", "LICENSE.md", "LICENSE.txt", "COPYING"}
# Section 8 of the language audit, plus the work-unit stem and the short stems
# called out for the gate. Order is the audit order, then the extra stem.
TOKEN_CODES: tuple[tuple[int, ...], ...] = (
    (100, 101, 109, 97, 110, 100, 97),
    (100, 101, 109, 97, 110, 100, 97, 115),
    (115, 111, 108, 105, 99, 105, 116, 97, 110, 116, 101),
    (114, 101, 115, 112, 111, 110, 115, 97, 118, 101, 108),
    (114, 101, 115, 112, 111, 110, 115, 225, 118, 101, 108),
    (97, 99, 101, 105, 116, 101),
    (99, 114, 105, 116, 101, 114, 105, 111),
    (99, 114, 105, 116, 233, 114, 105, 111),
    (99, 114, 105, 116, 101, 114, 105, 111, 115),
    (99, 114, 105, 116, 233, 114, 105, 111, 115),
    (118, 97, 108, 105, 100, 97, 99, 97, 111),
    (118, 97, 108, 105, 100, 97, 231, 227, 111),
    (118, 101, 114, 105, 102, 105, 99, 97, 99, 97, 111),
    (118, 101, 114, 105, 102, 105, 99, 97, 231, 227, 111),
    (118, 101, 114, 105, 102, 105, 99, 97, 99, 111, 101, 115),
    (118, 101, 114, 105, 102, 105, 99, 97, 231, 245, 101, 115),
    (99, 111, 110, 104, 101, 99, 105, 109, 101, 110, 116, 111),
    (112, 114, 111, 100, 117, 116, 111, 115),
    (112, 114, 111, 100, 117, 116, 111),
    (97, 117, 116, 111, 109, 97, 99, 97, 111),
    (97, 117, 116, 111, 109, 97, 231, 227, 111),
    (97, 117, 116, 111, 109, 97, 99, 111, 101, 115),
    (97, 117, 116, 111, 109, 97, 231, 245, 101, 115),
    (101, 110, 116, 114, 101, 103, 97),
    (101, 110, 116, 114, 101, 103, 97, 115),
    (102, 101, 99, 104, 97, 109, 101, 110, 116, 111),
    (114, 101, 103, 105, 115, 116, 114, 111),
    (99, 111, 110, 116, 114, 97, 116, 111),
    (102, 111, 110, 116, 101),
    (102, 111, 110, 116, 101, 115),
    (97, 110, 97, 108, 105, 115, 101),
    (97, 110, 225, 108, 105, 115, 101),
    (114, 101, 108, 97, 116, 111, 114, 105, 111),
    (114, 101, 108, 97, 116, 243, 114, 105, 111),
    (112, 97, 114, 99, 105, 97, 108),
    (112, 97, 114, 99, 105, 97, 105, 115),
    (98, 108, 111, 113, 117, 101, 97, 100, 111),
    (98, 108, 111, 113, 117, 101, 97, 100, 97),
    (98, 108, 111, 113, 117, 101, 97, 100, 111, 115),
    (98, 108, 111, 113, 117, 101, 97, 100, 97, 115),
    (98, 108, 111, 113, 117, 101, 97, 100),
    (99, 101, 114, 116, 105, 102, 105, 99, 97, 100, 97),
    (99, 101, 114, 116, 105, 102, 105, 99, 97, 100, 111),
    (99, 101, 114, 116, 105, 102, 105, 99, 97, 100, 97, 115),
    (105, 110, 100, 105, 99, 97, 116, 105, 118, 97),
    (105, 110, 100, 105, 99, 97, 116, 105, 118, 111),
    (105, 110, 100, 105, 99, 97, 116, 105, 118, 97, 115),
    (97, 98, 101, 114, 116, 97),
    (97, 98, 101, 114, 116, 111),
    (102, 101, 99, 104, 97, 100, 97),
    (102, 101, 99, 104, 97, 100, 111),
    (112, 97, 117, 115, 97, 100, 97),
    (97, 110, 100, 97, 109, 101, 110, 116, 111),
    (101, 109, 95, 115, 112, 101, 99),
    (101, 109, 95, 98, 117, 105, 108, 100),
    (101, 109, 95, 105, 110, 116, 101, 114, 112, 114, 101, 116, 97, 99, 97, 111),
    (105, 110, 116, 101, 114, 112, 114, 101, 116, 97, 99, 97, 111),
    (105, 110, 116, 101, 114, 112, 114, 101, 116, 97, 231, 227, 111),
    (109, 101, 116, 114, 105, 99, 97),
    (109, 233, 116, 114, 105, 99, 97),
    (109, 101, 116, 114, 105, 99, 97, 115),
    (109, 233, 116, 114, 105, 99, 97, 115),
    (109, 97, 116, 117, 114, 105, 100, 97, 100, 101),
    (114, 101, 99, 101, 105, 116, 97),
    (99, 111, 110, 118, 101, 114, 115, 97, 111),
    (99, 111, 110, 118, 101, 114, 115, 227, 111),
    (114, 101, 99, 111, 109, 112, 114, 97),
    (102, 114, 101, 116, 101),
    (112, 97, 114, 116, 105, 99, 105, 112, 97, 99, 97, 111),
    (112, 97, 114, 116, 105, 99, 105, 112, 97, 231, 227, 111),
    (99, 111, 109, 101, 114, 99, 105, 111),
    (99, 111, 109, 233, 114, 99, 105, 111),
    (109, 101, 110, 115, 97, 108),
    (114, 97, 112, 105, 100, 97),
    (114, 225, 112, 105, 100, 97),
    (114, 97, 112, 105, 100, 97, 115),
    (114, 225, 112, 105, 100, 97, 115),
    (110, 111, 116, 97, 115),
    (99, 111, 110, 99, 101, 105, 116, 111, 115),
    (99, 97, 116, 97, 108, 111, 103, 111),
    (99, 97, 116, 225, 108, 111, 103, 111),
    (110, 111, 118, 97, 45, 100, 101, 109, 97, 110, 100, 97),
    (102, 101, 99, 104, 97, 114, 45, 100, 101, 109, 97, 110, 100, 97),
    (119, 111, 114, 107, 116, 114, 101, 101, 45, 100, 101, 109, 97, 110, 100, 97),
    (100, 101, 109, 97, 110, 100, 95, 119, 111, 114, 107, 116, 114, 101, 101),
    (114, 117, 110, 95, 100, 101, 109, 97, 110, 100),
    (110, 97, 111),
    (110, 227, 111),
    (118, 111, 99, 101),
    (118, 111, 99, 234),
    (116, 97, 109, 98, 101, 109),
    (116, 97, 109, 98, 233, 109),
    (115, 227, 111),
    (101, 115, 116, 225),
    (101, 115, 116, 227, 111),
    (101, 110, 116, 227, 111),
    (115, 243),
    (106, 225),
    (224,),
    (113, 117, 234),
    (100, 101, 109, 97, 110, 100),
)


def tokens() -> tuple[str, ...]:
    return tuple("".join(chr(code) for code in codes) for codes in TOKEN_CODES)


def is_excluded(relative: str) -> bool:
    return Path(relative).name in EXCLUDED_NAMES


def scan_text(relative: str, text: str) -> list[str]:
    if is_excluded(relative):
        return []
    folded_tokens = tuple(token.casefold() for token in tokens())
    problems: list[str] = []
    for line_number, line in enumerate(text.splitlines(), start=1):
        folded = line.casefold()
        for token in folded_tokens:
            if token in folded:
                problems.append(f"{relative}:{line_number}: {token}")
        for char in line:
            if char.isalpha() and ord(char) > 127:
                problems.append(f"{relative}:{line_number}: accented letter U+{ord(char):04X}")
                break
    return problems


def tracked_files(root: Path) -> list[str]:
    result = subprocess.run(
        ["git", "ls-files", "-co", "--exclude-standard", "-z"],
        cwd=root,
        check=True,
        capture_output=True,
    )
    names = [item.decode() for item in result.stdout.split(b"\0") if item]
    return sorted(names)


def scan_repository(root: Path = ROOT) -> list[str]:
    problems: list[str] = []
    for relative in tracked_files(root):
        path = root / relative
        if not path.is_file():
            continue
        data = path.read_bytes()
        if b"\0" in data:
            problems.append(f"{relative}: binary file")
            continue
        try:
            text = data.decode("utf-8")
        except UnicodeDecodeError:
            problems.append(f"{relative}: not utf-8")
            continue
        problems.extend(scan_text(relative, text))
    return problems


def main() -> int:
    problems = scan_repository(ROOT)
    if problems:
        print("language: Portuguese tokens or accented letters found.")
        for problem in problems:
            print(f"language: {problem}")
        return 1
    print("language: English only.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
