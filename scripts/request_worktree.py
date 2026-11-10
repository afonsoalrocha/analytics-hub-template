"""Print the git commands for one request worktree.

The script prints commands and does not run them. Closing a request merges
with ``--no-ff`` so the request stays visible as its own commit.
"""

from __future__ import annotations

import argparse
import re
import sys

_ID = re.compile(r"\d{3}")
_SLUG = re.compile(r"[a-z0-9]+(?:-[a-z0-9]+)*")


def branch_name(request_id: str, slug: str) -> str:
    if _ID.fullmatch(request_id) is None:
        raise ValueError("Request id must be three digits.")
    if _SLUG.fullmatch(slug) is None:
        raise ValueError("Slug must be lowercase words separated by hyphens.")
    return f"worktree-request-{request_id}-{slug}"


def open_commands(request_id: str, slug: str, base: str = "main") -> list[str]:
    name = branch_name(request_id, slug)
    _check_base(base)
    return [f"git worktree add ../{name} -b {name} {base}"]


def close_commands(request_id: str, slug: str, base: str = "main") -> list[str]:
    name = branch_name(request_id, slug)
    _check_base(base)
    return [
        f"git checkout {base}",
        f"git merge --no-ff {name}",
        f"git worktree remove ../{name}",
    ]


def _check_base(base: str) -> None:
    if not base or any(character.isspace() for character in base):
        raise ValueError("Base branch must be a single git ref.")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Print worktree commands for one request.")
    parser.add_argument("action", choices=("open", "close"))
    parser.add_argument("request_id")
    parser.add_argument("slug")
    parser.add_argument("--base", default="main")
    args = parser.parse_args(argv)
    try:
        if args.action == "open":
            commands = open_commands(args.request_id, args.slug, args.base)
        else:
            commands = close_commands(args.request_id, args.slug, args.base)
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        return 1
    print("\n".join(commands))
    return 0


if __name__ == "__main__":
    sys.exit(main())
