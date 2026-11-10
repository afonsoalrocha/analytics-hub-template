"""Start an MCP server with credentials from the local environment.

``.mcp.json`` names this script and a server id. It holds no token. An
optional OAuth profile outside the repository may supply an access token
when ``read_only`` is true.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from collections.abc import Mapping
from pathlib import Path

from paths import ROOT

SERVERS = {
    "filesystem": ("npx", "-y", "@modelcontextprotocol/server-filesystem"),
}
SECRET_KEYS = frozenset(
    {"token", "password", "secret", "api_key", "access_token", "pat", "authorization"}
)
SECRET_SNIPPETS = ("bearer ", "ghp_", "sk-")
DEFAULT_PROFILE = Path.home() / ".config" / "analytics-hub" / "oauth-readonly.json"


def command_for(server: str, env: Mapping[str, str]) -> list[str]:
    if server not in SERVERS:
        raise ValueError(f"Unknown MCP server {server}.")
    root = env.get("MCP_FILESYSTEM_ROOT", ".").strip() or "."
    return [*SERVERS[server], root]


def resolve_profile(env: Mapping[str, str]) -> Path:
    raw = env.get("MCP_OAUTH_PROFILE", "").strip()
    if not raw:
        return DEFAULT_PROFILE
    return Path(raw).expanduser()


def profile_env(path: Path, repo_root: Path) -> dict[str, str]:
    resolved = path.expanduser().resolve()
    repo = repo_root.resolve()
    if resolved == repo or repo in resolved.parents:
        raise ValueError("OAuth profile must live outside the repository.")
    if not resolved.is_file():
        return {}
    try:
        data = json.loads(resolved.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError("OAuth profile is not valid JSON.") from exc
    if not isinstance(data, dict) or data.get("read_only") is not True:
        raise ValueError("OAuth profile must set read_only to true.")
    token = data.get("access_token", "")
    if token and not isinstance(token, str):
        raise ValueError("OAuth access_token must be a string.")
    if not token:
        return {}
    return {"MCP_ACCESS_TOKEN": token}


def plan(server: str, env: Mapping[str, str], repo_root: Path) -> tuple[list[str], dict[str, str]]:
    argv = command_for(server, env)
    extra = profile_env(resolve_profile(env), repo_root)
    token = extra.get("MCP_ACCESS_TOKEN", "")
    if token and any(token in part for part in argv):
        raise ValueError("Refusing to put an access token on the MCP command line.")
    return argv, extra


def audit_config(root: Path = ROOT) -> list[str]:
    path = root / ".mcp.json"
    try:
        document = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return [f".mcp.json is unreadable ({exc})."]
    problems: list[str] = []
    _walk(document, problems)
    if "mcp_wrapper.py" not in path.read_text(encoding="utf-8"):
        problems.append(".mcp.json must start scripts/mcp_wrapper.py.")
    return problems


def _walk(value: object, problems: list[str]) -> None:
    if isinstance(value, dict):
        for key, child in value.items():
            if str(key).lower() in SECRET_KEYS:
                problems.append(f".mcp.json contains secret key {key}.")
            _walk(child, problems)
        return
    if isinstance(value, list):
        for child in value:
            _walk(child, problems)
        return
    if isinstance(value, str):
        lowered = value.lower()
        if any(snippet in lowered for snippet in SECRET_SNIPPETS):
            problems.append(".mcp.json contains a credential-like value.")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Start an MCP server from the local environment.")
    parser.add_argument("server")
    args = parser.parse_args(argv)
    try:
        command, extra = plan(args.server, os.environ, ROOT)
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        return 1
    env = os.environ.copy()
    env.update(extra)
    os.execvpe(command[0], command, env)
    return 1


if __name__ == "__main__":
    sys.exit(main())
