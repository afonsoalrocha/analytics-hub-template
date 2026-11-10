"""Render the skills catalog in CLAUDE.md from skill frontmatter.

The Markdown table between the skills markers is generated. ``--check``
fails when the committed table drifts from ``.claude/skills/*/SKILL.md``.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import yaml

from paths import ROOT

START = "<!-- skills:start -->"
END = "<!-- skills:end -->"


def load_skills(root: Path = ROOT) -> list[dict[str, str]]:
    base = root / ".claude" / "skills"
    if not base.is_dir():
        raise ValueError(".claude/skills is missing.")
    skills: list[dict[str, str]] = []
    for path in sorted(base.glob("*/SKILL.md")):
        meta = _frontmatter(path.read_text(encoding="utf-8"), path)
        name = str(meta.get("name", "")).strip()
        description = " ".join(str(meta.get("description", "")).split())
        if not name or not description:
            raise ValueError(f"{path.name} needs name and description in frontmatter.")
        skills.append(
            {
                "name": name,
                "description": description,
                "path": path.relative_to(root).as_posix(),
            }
        )
    skills.sort(key=lambda item: item["name"])
    if not skills:
        raise ValueError(".claude/skills has no SKILL.md files.")
    return skills


def render_block(root: Path = ROOT) -> str:
    lines = [START, "| Skill | Path | Description |", "| --- | --- | --- |"]
    for skill in load_skills(root):
        lines.append(f"| `{skill['name']}` | `{skill['path']}` | {skill['description']} |")
    lines.append(END)
    return "\n".join(lines)


def splice(text: str, block: str) -> str:
    start = text.find(START)
    end = text.find(END)
    if start < 0 or end < 0 or end < start:
        raise ValueError("CLAUDE.md is missing skills markers.")
    if text.find(START, start + len(START)) >= 0:
        raise ValueError("CLAUDE.md has more than one skills catalog.")
    return text[:start] + block + text[end + len(END) :]


def drift(root: Path = ROOT) -> list[str]:
    path = root / "CLAUDE.md"
    try:
        updated = splice(path.read_text(encoding="utf-8"), render_block(root))
    except (OSError, ValueError, yaml.YAMLError) as exc:
        return [str(exc)]
    current = path.read_text(encoding="utf-8")
    if updated != current:
        return ["CLAUDE.md skills catalog is out of date. Run python scripts/render_skills.py."]
    return []


def _frontmatter(text: str, path: Path) -> dict[str, object]:
    if not text.startswith("---\n"):
        raise ValueError(f"{path.name} needs YAML frontmatter.")
    end = text.find("\n---", 4)
    if end < 0:
        raise ValueError(f"{path.name} frontmatter is not closed.")
    data = yaml.safe_load(text[4:end])
    if not isinstance(data, dict):
        raise ValueError(f"{path.name} frontmatter must be a mapping.")
    return data


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Render the CLAUDE.md skills catalog.")
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args(argv)
    if args.check:
        problems = drift(ROOT)
        if problems:
            for problem in problems:
                print(f"render-skills: {problem}")
            return 1
        print("render-skills: CLAUDE.md matches the skill frontmatter.")
        return 0
    path = ROOT / "CLAUDE.md"
    try:
        updated = splice(path.read_text(encoding="utf-8"), render_block(ROOT))
    except (OSError, ValueError, yaml.YAMLError) as exc:
        print(f"render-skills: {exc}", file=sys.stderr)
        return 1
    path.write_text(updated, encoding="utf-8")
    print("render-skills: wrote CLAUDE.md")
    return 0


if __name__ == "__main__":
    sys.exit(main())
