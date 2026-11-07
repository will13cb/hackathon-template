#!/usr/bin/env python3
"""PreToolUse guard for Bash. Exit 2 blocks the command and shows stderr to Claude.

Blocks:
  * destructive cloud commands (aws ... delete-*, gcloud ... delete, gsutil rm, bq rm,
    teardown scripts)
  * destructive git (push --force, reset --hard, clean -f)
  * rm -r on dangerous targets (/, ~, ., .., *, .git, absolute paths outside /tmp)
  * committing secrets (.env files, keys, service-account JSON, key-shaped strings)

The human can still run any of these in their own terminal. That's intentional.
"""

from __future__ import annotations

import json
import re
import shlex
import subprocess
import sys
from pathlib import Path

SEG = r"[^|;&\n]*"  # stay inside one shell segment

BLOCK_PATTERNS: list[tuple[str, str]] = [
    # --- cloud deletes ---
    (
        rf"\baws\b{SEG}\s(delete|terminate|remove|deregister|purge|detach)-[\w-]+",
        "destructive AWS command",
    ),
    (r"\baws\s+s3\s+(rm|rb)\b", "deleting S3 objects/buckets"),
    (rf"\baws\s+s3\s+sync\b{SEG}\s--delete\b", "aws s3 sync --delete"),
    (rf"\bgcloud\b{SEG}\s(delete|remove-iam-policy-binding)\b", "destructive gcloud command"),
    (r"\bgcloud\s+storage\s+(rm|buckets\s+delete)\b", "deleting GCS objects/buckets"),
    (rf"\bgsutil\b{SEG}\s(rm|rb)\b", "deleting GCS objects/buckets"),
    (r"\bbq\s+rm\b", "deleting BigQuery resources"),
    (r"teardown[\w-]*\.sh\b|\bmake\b[^|;&\n]*\bteardown", "teardown scripts are human-only"),
    # --- git history destruction ---
    (
        rf"\bgit\s+push\b{SEG}\s(--force(?![-\w])|-f\b)",
        "git push --force (use --force-with-lease if truly needed, and ask first)",
    ),
    (rf"\bgit\s+push\b{SEG}\s\+\S", "force push via +refspec"),
    (rf"\bgit\s+reset\b{SEG}\s--hard\b", "git reset --hard discards work"),
    (rf"\bgit\s+clean\b{SEG}\s-\w*f", "git clean -f deletes untracked files"),
    (rf"\bgit\s+add\b{SEG}\s(-f|--force)\b", "git add --force bypasses .gitignore"),
]

DANGEROUS_RM_TARGETS = {
    "/",
    "/*",
    "~",
    "~/",
    "~/*",
    "$HOME",
    "${HOME}",
    ".",
    "./",
    "./*",
    "..",
    "../",
    "*",
    ".git",
    ".git/",
}

SECRET_NAME = re.compile(
    r"(^|/)("
    r"\.env(\.(?!example$|sample$|template$)[\w.-]+)?"  # .env, .env.local — not .env.example
    r"|.*\.pem|.*\.key|.*\.p12|.*\.pfx|id_rsa.*|id_ed25519.*"
    r"|.*service[-_]?account.*\.json|.*credentials.*\.json|application_default_credentials\.json"
    r"|\.aws/credentials|terraform\.tfstate.*"
    r")$",
    re.IGNORECASE,
)

SECRET_CONTENT = [
    (re.compile(r"\b(AKIA|ASIA)[0-9A-Z]{16}\b"), "AWS access key id"),
    (re.compile(r"aws_secret_access_key\s*[=:]\s*['\"]?[A-Za-z0-9/+=]{40}"), "AWS secret key"),
    (re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----"), "private key"),
    (re.compile(r"\"type\":\s*\"service_account\""), "GCP service-account key"),
    (re.compile(r"\bAIza[0-9A-Za-z_\-]{35}\b"), "Google API key"),
    (re.compile(r"\bsk-ant-[A-Za-z0-9_\-]{20,}"), "Anthropic API key"),
    (re.compile(r"\bsk-(proj-)?[A-Za-z0-9_\-]{32,}"), "OpenAI-style API key"),
    (re.compile(r"\bgh[pousr]_[A-Za-z0-9]{36,}\b"), "GitHub token"),
    (re.compile(r"\bxox[baprs]-[A-Za-z0-9-]{10,}"), "Slack token"),
]


def block(reason: str, command: str) -> None:
    print(
        f"BLOCKED by .claude/hooks/guard_bash.py: {reason}.\n"
        f"Command: {command}\n"
        "Don't try to work around this guard. If the action is really needed, explain why and "
        "ask the user to run it in their own terminal.",
        file=sys.stderr,
    )
    sys.exit(2)


def check_patterns(cmd: str) -> None:
    for pattern, reason in BLOCK_PATTERNS:
        if re.search(pattern, cmd):
            block(reason, cmd)


def tokenize(cmd: str) -> list[str]:
    try:
        lex = shlex.shlex(cmd, posix=True, punctuation_chars=";&|")
        lex.whitespace_split = True
        return list(lex)
    except ValueError:
        return cmd.split()


def check_rm(tokens: list[str], cmd: str) -> None:
    separators = {";", "&&", "||", "|", "&"}
    i = 0
    while i < len(tokens):
        tok = tokens[i]
        if tok == "rm" or tok.endswith("/rm"):
            args = []
            j = i + 1
            while j < len(tokens) and tokens[j] not in separators:
                args.append(tokens[j])
                j += 1
            flags = "".join(
                a.lstrip("-") for a in args if a.startswith("-") and not a.startswith("--")
            )
            recursive = "r" in flags.lower() or "--recursive" in args
            targets = [a for a in args if not a.startswith("-")]
            if recursive:
                for t in targets:
                    bad = (
                        t in DANGEROUS_RM_TARGETS
                        or t.startswith(("~", "$HOME", "${HOME}", ".."))
                        or (t.startswith("/") and not t.startswith("/tmp/"))
                    )
                    if bad:
                        block(f"rm -r on a dangerous target ({t!r})", cmd)
            i = j
        else:
            i += 1


def git(cwd: str, *args: str) -> str:
    try:
        return subprocess.run(
            ["git", *args], cwd=cwd, capture_output=True, text=True, timeout=10
        ).stdout
    except Exception:
        return ""


def check_secrets(tokens: list[str], cmd: str, cwd: str) -> None:
    if not re.search(r"\bgit\b", cmd):
        return

    # 1) explicit `git add <secret file>`
    if re.search(r"\bgit\s+add\b", cmd):
        for t in tokens:
            if SECRET_NAME.search(t):
                block(f"staging a secret-looking file ({t})", cmd)

    if not re.search(r"\bgit\s+commit\b", cmd):
        return

    # 2) what will this commit contain?
    files = set(git(cwd, "diff", "--cached", "--name-only").split())
    diff = git(cwd, "diff", "--cached", "-U0")
    if re.search(rf"\bgit\s+add\b|\bgit\s+commit\b{SEG}\s-\w*a", cmd):
        # Covers `git add -A && git commit` and `git commit -a`: include working-tree changes too.
        files |= set(git(cwd, "diff", "--name-only").split())
        diff += git(cwd, "diff", "-U0")
        for f in git(cwd, "ls-files", "--others", "--exclude-standard").split():
            files.add(f)
            p = Path(cwd, f)
            try:
                if p.is_file() and p.stat().st_size < 1_000_000:
                    diff += "\n" + p.read_text(errors="ignore")
            except OSError:
                pass

    for f in sorted(files):
        if SECRET_NAME.search(f):
            block(
                f"commit would include a secret-looking file ({f}). "
                "Unstage it and add it to .gitignore",
                cmd,
            )

    added = "\n".join(
        line for line in diff.splitlines() if not line.startswith(("---", "+++", "-"))
    )
    for rx, label in SECRET_CONTENT:
        m = rx.search(added)
        if m:
            snippet = m.group(0)[:8] + "…"
            block(
                f"commit would include what looks like a {label} ({snippet}). "
                "Move it to .env or a secret manager",
                cmd,
            )


def main() -> None:
    try:
        data = json.load(sys.stdin)
    except json.JSONDecodeError:
        sys.exit(0)
    if data.get("tool_name") != "Bash":
        sys.exit(0)
    cmd = (data.get("tool_input") or {}).get("command", "") or ""
    cwd = data.get("cwd") or "."
    tokens = tokenize(cmd)
    check_patterns(cmd)
    check_rm(tokens, cmd)
    check_secrets(tokens, cmd, cwd)
    sys.exit(0)


if __name__ == "__main__":
    main()
