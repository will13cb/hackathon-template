#!/usr/bin/env python3
"""Kickoff helper: keep one cloud, delete the other cloud's scaffolding.

    make use-aws      # keep AWS (Bedrock + Lambda), drop GCP
    make use-gcp      # keep GCP (Gemini + Cloud Run), drop AWS

Removes the other cloud's deploy/teardown scripts, MCP servers, SDK dependency, Makefile targets
and .env keys, then records CLOUD=<kept> so `make doctor` only checks that cloud.
Everything removed is tracked in git, so `git checkout -- .` undoes it before you commit.
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
from pathlib import Path

PLAN = {
    # kept cloud -> what to remove
    "aws": {
        "files": ["deploy/gcp-cloudrun.sh", "deploy/teardown-gcp.sh", ".gcloudignore"],
        "mcp": ["cloud-run", "gcloud"],
        "reqs": ["google-genai"],
        "make": ["deploy-gcp", "logs-gcp", "teardown-gcp"],
        "env_section": "Google",
        "provider": "bedrock",
    },
    "gcp": {
        "files": [
            "deploy/aws-lambda.sh",
            "deploy/aws-bootstrap.sh",
            "deploy/teardown-aws.sh",
            "deploy/iam",
        ],
        "mcp": ["aws", "aws-knowledge"],
        "reqs": ["boto3"],
        "make": ["deploy-aws", "aws-bootstrap", "logs-aws", "teardown-aws"],
        "env_section": "AWS",
        "provider": "vertex",
    },
}


def prune_makefile(text: str, targets: list[str]) -> str:
    out, skipping = [], False
    for line in text.splitlines(keepends=True):
        name = re.match(r"^([A-Za-z0-9_-]+):", line)
        if name:
            skipping = name.group(1) in targets
        elif skipping and not line.startswith("\t") and line.strip():
            skipping = False
        if skipping:
            continue
        out.append(line)
    text = "".join(out)
    for t in targets:
        text = re.sub(rf"[ \t]+{re.escape(t)}\b(?=[ \t\\]|$)", "", text, flags=re.M)
    return re.sub(r"\n{3,}", "\n\n", text)


def prune_env(text: str, section_word: str, kept: str, provider: str) -> str:
    """Drop `# --- ... <section_word> ... ---` sections; set CLOUD and LLM_PROVIDER."""
    out, skipping = [], False
    for line in text.splitlines(keepends=True):
        if line.startswith("# ---"):
            skipping = section_word in line
        if not skipping:
            out.append(line)
    text = "".join(out).rstrip("\n") + "\n"
    text = re.sub(r"^LLM_PROVIDER=\S*", f"LLM_PROVIDER={provider}", text, flags=re.M)
    return f"CLOUD={kept}                        # set by make use-{kept}\n" + text


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("cloud", choices=sorted(PLAN))
    ap.add_argument("--root", default=Path(__file__).resolve().parents[1], type=Path)
    a = ap.parse_args()
    root, plan = a.root, PLAN[a.cloud]

    env_example = root / ".env.example"
    if re.search(r"^CLOUD=", env_example.read_text(), re.M):
        raise SystemExit("Already pruned (CLOUD= is set in .env.example). Nothing to do.")

    for f in plan["files"]:
        p = root / f
        if p.is_dir():
            shutil.rmtree(p)
        elif p.exists():
            p.unlink()

    mcp = root / ".mcp.json"
    cfg = json.loads(mcp.read_text())
    for name in plan["mcp"]:
        cfg["mcpServers"].pop(name, None)
    mcp.write_text(json.dumps(cfg, indent=2) + "\n")

    req = root / "requirements.txt"
    req.write_text(
        "".join(
            line
            for line in req.read_text().splitlines(keepends=True)
            if not any(line.strip().startswith(r) for r in plan["reqs"])
        )
    )

    mk = root / "Makefile"
    mk.write_text(prune_makefile(mk.read_text(), plan["make"]))

    for env in (env_example, root / ".env"):
        if env.exists():
            env.write_text(
                prune_env(env.read_text(), plan["env_section"], a.cloud, plan["provider"])
            )

    claude = root / "CLAUDE.md"
    if claude.exists():
        claude.write_text(
            claude.read_text().rstrip("\n")
            + f"\n- make use-{a.cloud}: removed the other cloud's scaffolding (one cloud = less"
            " to break).\n"
        )

    print(f"Kept {a.cloud}. Removed: {', '.join(plan['files'] + plan['mcp'] + plan['reqs'])}.")
    print("Review with `git diff`, then commit. Undo (before committing): git checkout -- .")


if __name__ == "__main__":
    main()
