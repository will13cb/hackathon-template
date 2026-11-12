#!/usr/bin/env python3
"""Pin every npx/uvx MCP server in .mcp.json to an exact version.

`@latest` means an upstream release on the morning of the event can break your setup.
Run this the week before (`make pin-mcp`), check `make doctor` and that Claude Code's /mcp
shows the servers connected, then commit .mcp.json.

    python scripts/pin_mcp.py            # resolve current versions and write .mcp.json
    python scripts/pin_mcp.py --check    # exit 1 if anything is unpinned (for CI)
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def split_spec(spec: str) -> tuple[str, str]:
    """'@scope/pkg@1.2.3' -> ('@scope/pkg', '1.2.3'); 'pkg' -> ('pkg', '')."""
    at = spec.rfind("@")
    return (spec[:at], spec[at + 1 :]) if at > 0 else (spec, "")


def package_index(server: dict) -> int | None:
    """Index in args of the package spec for npx/uvx servers, else None."""
    if server.get("command") not in ("npx", "uvx"):
        return None
    for i, a in enumerate(server.get("args", [])):
        if not a.startswith("-"):
            return i
    return None


def resolve(command: str, pkg: str) -> str:
    if command == "npx":
        out = subprocess.run(["npm", "view", pkg, "version"], capture_output=True, text=True)
        if out.returncode:
            raise RuntimeError(out.stderr.strip())
        return out.stdout.strip()
    with urllib.request.urlopen(f"https://pypi.org/pypi/{pkg}/json", timeout=20) as r:
        return json.load(r)["info"]["version"]


def pin(cfg: dict, resolver=resolve) -> list[str]:
    changes = []
    for name, server in cfg.get("mcpServers", {}).items():
        i = package_index(server)
        if i is None:
            continue
        pkg, ver = split_spec(server["args"][i])
        if ver and ver != "latest":
            continue
        new = resolver(server["command"], pkg)
        server["args"][i] = f"{pkg}@{new}"
        changes.append(f"{name}: {pkg} -> {new}")
    return changes


def unpinned(cfg: dict) -> list[str]:
    bad = []
    for name, server in cfg.get("mcpServers", {}).items():
        i = package_index(server)
        if i is not None and split_spec(server["args"][i])[1] in ("", "latest"):
            bad.append(name)
    return bad


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true")
    ap.add_argument("--file", type=Path, default=ROOT / ".mcp.json")
    a = ap.parse_args()
    cfg = json.loads(a.file.read_text())
    if a.check:
        bad = unpinned(cfg)
        if bad:
            sys.exit(f"Unpinned MCP servers: {', '.join(bad)}. Run: make pin-mcp")
        print("All MCP servers pinned.")
        return
    changes = pin(cfg)
    a.file.write_text(json.dumps(cfg, indent=2) + "\n")
    print("\n".join(changes) or "Already pinned.")
    print("Now: restart Claude Code, check /mcp shows them connected, then commit .mcp.json.")


if __name__ == "__main__":
    main()
