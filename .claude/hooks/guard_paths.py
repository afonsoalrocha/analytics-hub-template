#!/usr/bin/env python3
"""Block secret files, temp paths, and interpreters outside .venv.

The hook reads one JSON object from stdin. ``tool_name`` or ``tool`` names
the tool. ``tool_input`` or ``input`` carries ``file_path`` or ``command``.
Exit 0 allows the call. Exit 2 blocks it and prints the reason on stderr.
An empty stdin is allowed so a manual run stays quiet.

``.env.example`` stays readable. ``python3 -m venv .venv`` stays allowed so
the environment can be created. Every later Python, pip, pytest, dbt, ruff,
or sqlfluff invocation has to be ``.venv/bin/...``.
"""

from __future__ import annotations

import json
import re
import sys

ALLOWED_DOTENV = {".env.example", ".env.sample", ".env.template"}
TEMP_PARTS = {"tmp", "temp"}
_INTERPRETER = re.compile(r"^(?:python\d*(?:\.\d+)?|pip\d*(?:\.\d+)?|pytest|dbt|ruff|sqlfluff)$")
_DOTENV = re.compile(r"(?:^|[\\/\s'\"=])(\.env(?:\.[A-Za-z0-9_-]+)?)(?=$|[\s'\"|&;<>])")
_ASSIGNMENT = re.compile(r"[A-Za-z_][A-Za-z0-9_]*=\S*")
_SPLIT = re.compile(r"&&|\|\||;|\n")

ENV_MESSAGE = "Reading or writing .env is blocked. Use .env.example and the process environment."
TEMP_MESSAGE = "Temp folders are blocked. Keep working files in the repository."


def evaluate(tool_name: str, tool_input: dict[str, object]) -> tuple[bool, str]:
    del tool_name
    for key in ("file_path", "path", "target_file", "notebook_path", "file"):
        value = tool_input.get(key)
        if isinstance(value, str):
            reason = path_block_reason(value)
            if reason:
                return False, reason
    command = tool_input.get("command")
    if isinstance(command, str):
        reason = command_block_reason(command)
        if reason:
            return False, reason
    return True, ""


def path_block_reason(raw: str) -> str | None:
    text = raw.strip().strip("'\"")
    if not text or text.startswith("-") or "://" in text:
        return None
    normalized = text.replace("\\", "/")
    name = normalized.rstrip("/").split("/")[-1]
    if name == ".env" or (name.startswith(".env.") and name not in ALLOWED_DOTENV):
        return ENV_MESSAGE
    if name.endswith(".tmp"):
        return "Temp files are blocked. Keep working files in the repository."
    parts = [part for part in normalized.split("/") if part not in {"", "."}]
    if any(part.lower() in TEMP_PARTS for part in parts):
        return TEMP_MESSAGE
    return None


def command_block_reason(command: str) -> str | None:
    if _dotenv_reason(command):
        return ENV_MESSAGE
    for segment in _SPLIT.split(command):
        reason = _segment_reason(segment)
        if reason:
            return reason
    return None


def _dotenv_reason(command: str) -> bool:
    return any(match.group(1) not in ALLOWED_DOTENV for match in _DOTENV.finditer(command))


def _segment_reason(segment: str) -> str | None:
    tokens = segment.split()
    index = 0
    while index < len(tokens) and _ASSIGNMENT.fullmatch(tokens[index].strip("'\"")):
        index += 1
    if index >= len(tokens):
        return None
    binary = tokens[index].strip("'\"")
    rest = [token.strip("'\"") for token in tokens[index + 1 :]]
    for token in (binary, *rest):
        reason = path_block_reason(token)
        if reason:
            return reason
    base = binary.replace("\\", "/").rstrip("/").split("/")[-1]
    if _INTERPRETER.fullmatch(base) is None:
        return None
    if _is_venv_binary(binary):
        return None
    if base.startswith("python") and rest[:3] == ["-m", "venv", ".venv"]:
        return None
    preferred = "python" if base == "python" else base
    return f"Use .venv/bin/{preferred} instead of {binary}."


def _is_venv_binary(binary: str) -> bool:
    normalized = "/" + binary.replace("\\", "/").lstrip("/")
    return "/.venv/bin/" in normalized or "/.venv/Scripts/" in normalized


def main() -> int:
    raw = sys.stdin.read()
    if not raw.strip():
        return 0
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError:
        print("Path guard received invalid JSON.", file=sys.stderr)
        return 2
    if not isinstance(payload, dict):
        print("Path guard expected a JSON object.", file=sys.stderr)
        return 2
    tool_input = payload.get("tool_input")
    if tool_input is None:
        tool_input = payload.get("input")
    if not isinstance(tool_input, dict):
        tool_input = {}
    tool_name = str(payload.get("tool_name") or payload.get("tool") or "")
    allowed, message = evaluate(tool_name, tool_input)
    if not allowed:
        print(message, file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
